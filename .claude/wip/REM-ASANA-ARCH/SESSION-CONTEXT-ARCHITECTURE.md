# Session Context Architecture: REM-ASANA-ARCH

**Initiative**: 8-workstream architecture remediation for autom8y-asana
**Produced by**: Context Engineer analysis, 2026-02-23
**Scope**: Session decomposition, context flow, parallelization, token economics

---

## 1. Context Budget Analysis

### Fixed Costs Per Session (Unavoidable)

Every Claude Code session in this project pays these fixed costs on every turn:

| Component | Lines | Est. Tokens | Notes |
|-----------|-------|-------------|-------|
| System prompt (CC built-in) | -- | ~2,000 | Claude Code internal |
| CLAUDE.md chain (4 files) | ~390 | ~1,500 | Global + project + parent levels |
| MEMORY.md | ~99 | ~500 | Auto-injected, grows over initiative |
| SessionStart hook injection | ~30 | ~150 | Session context table |
| **Subtotal (fixed/turn)** | | **~4,150** | Paid every turn |

### Agent Invocation Costs (Per Task Tool Call)

When the main thread delegates to a specialist via Task tool, that specialist loads:

| Component | Lines | Est. Tokens | Notes |
|-----------|-------|-------------|-------|
| Agent prompt (avg) | ~170 | ~800 | pythia=255, architect=129, PE=132, QA=138 |
| Skills loaded by agent | ~200-400 | ~1,000-2,000 | doc-artifacts, standards, etc. |
| Task description from main | ~50-150 | ~300-700 | The prompt crafted by Pythia/main |
| **Subtotal (per delegation)** | | **~2,100-3,500** | Per specialist invocation |

### Seed File Costs (Loaded Once at Session Start)

| File | Lines | Est. Tokens | When Loaded |
|------|-------|-------------|-------------|
| PROMPT_0.md | 201 | ~900 | Every session (guardrails) |
| WS-QW.md | 129 | ~600 | WS-QW session only |
| WS-SYSCTX.md | 126 | ~600 | WS-SYSCTX sessions only |
| WS-DSC.md | 114 | ~550 | WS-DSC sessions only |
| WS-DFEX.md | 117 | ~550 | WS-DFEX sessions only |
| WS-CLASS.md | 121 | ~550 | WS-CLASS session only |
| WS-QUERY.md | 111 | ~500 | WS-QUERY sessions only |
| WS-HYGIENE.md | 145 | ~650 | WS-HYGIENE sessions only |
| WS-DEBT.md | 95 | ~450 | WS-DEBT session only |
| DEPENDENCY-GRAPH.md | 99 | ~450 | Hub thread only |
| UNKNOWNS-RESOLUTION.md | 272 | ~1,200 | Pre-flight session only |

### Deep-Dive Analysis Files (Load On-Demand ONLY)

These 4 files total 3,122 lines (~14,000 tokens). NEVER front-load them.

| File | Lines | When Referenced |
|------|-------|-----------------|
| TOPOLOGY-INVENTORY.md | 760 | When seed says "See Section X" |
| DEPENDENCY-MAP.md | 779 | When investigating cycle details |
| ARCHITECTURE-ASSESSMENT.md | 767 | When reviewing anti-pattern evidence |
| ARCHITECTURE-REPORT.md | 816 | When checking recommendation rationale |

**Rule**: Seed files contain all operational detail needed for execution. Deep-dive
files are evidence/rationale archives. Load a specific section only when a seed file
explicitly references it by section number.

---

## 2. Per-Workstream Session Launch Specifications

### Session Type Classification

| Type | Sessions | Rite | Agent Flow | Characteristics |
|------|----------|------|------------|-----------------|
| **PATCH-hygiene** | 1 | hygiene | PE direct (skip Pythia routing) | Small, scoped, low ceremony |
| **MODULE-hygiene** | 1-2 | hygiene | Pythia -> architect (optional) -> PE -> QA | Moderate, structured steps |
| **MODULE-10x** | 2-3 | 10x-dev | Pythia -> architect -> PE -> QA | Full lifecycle, TDD required |
| **PATCH-debt** | 1 | debt-triage | Investigation + decision | Audit-focused, minimal code |

---

### WS-QW (Quick Wins) -- 1 Session

**Type**: PATCH-hygiene
**Launch command**: `/start "WS-QW: Quick Wins" --complexity=PATCH`

**Session prompt (user types after @-refs)**:
```
Execute the WS-QW quick wins sprint. Four items: R-001, R-007, R-003, R-002.
Do them in that order. Each has a green-to-green gate in the seed file.
After all four, run full test suite. Update MEMORY.md when done.
```

**@-references (2 files)**:
1. `@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md` (guardrails)
2. `@.claude/wip/REM-ASANA-ARCH/WS-QW.md` (execution spec)

**Context budget**: ~4,150 (fixed) + 900 (PROMPT_0) + 600 (WS-QW) = ~5,650 tokens at start.
Leaves >95% of context window for execution.

**Agent routing**: For PATCH complexity, skip Pythia orchestration. The main thread
can execute R-001 through R-002 directly or delegate to principal-engineer. The seed
file IS the implementation plan -- no TDD phase needed.

**MEMORY.md writes on completion**:
```
## Completed Work (WS-QW)
- WS-QW Quick Wins: DONE [date]
  - R-001: conversation_audit.py bootstrap [verified|added]
  - R-007: cloudwatch.py bootstrap [documented|added]
  - R-003: Lifecycle canonical status documented
  - R-002: 3 helpers extracted to core/creation.py
  - U-003, U-007 resolved
```

---

### WS-SYSCTX (system_context Registration) -- 1-2 Sessions

**Type**: MODULE-hygiene
**Launch command**: `/start "WS-SYSCTX: system_context registration pattern" --complexity=MODULE`

**Session 1 prompt**:
```
Refactor system_context.py to use a registration pattern per the WS-SYSCTX seed.
Start with Step 1 (add registration API) and Step 2 (migrate SchemaRegistry).
Then migrate singletons 2-5 (one at a time, tests after each).
Emit a checkpoint before ending if not complete.
```

**Session 2 prompt (if needed)**:
```
Continue WS-SYSCTX. See checkpoint in MEMORY.md for progress.
Migrate remaining singletons, remove upward imports (Step 4),
run 3x stability check (Step 5). Update MEMORY.md when done.
```

**@-references (2 files)**:
1. `@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md`
2. `@.claude/wip/REM-ASANA-ARCH/WS-SYSCTX.md`

**Context budget**: ~5,650 tokens at start. Single-file refactor with iterative
test runs -- context grows primarily from test output, which is ephemeral.

**Agent routing**: Pythia routes to architect (brief -- design the registration
API interface) then principal-engineer for migration. For hygiene rite at MODULE
complexity, the architect phase is optional -- the seed file already contains
the design. Recommend principal-engineer direct entry.

**Checkpoint format (Session 1 -> Session 2)**:
```
## Checkpoint WS-SYSCTX [date]
Completed: Registration API added, singletons 1-5 migrated
Remaining: Singletons 6-8, Step 4 (remove imports), Step 5 (3x stability)
Decisions: Registration uses module-level list, not class-based registry
Test status: 10,552 passed after singleton 5
```

---

### WS-DSC (DataServiceClient Execution Policy) -- 2-3 Sessions

**Type**: MODULE-10x
**Launch command**: `/start "WS-DSC: DataServiceClient execution policy" --complexity=MODULE --rite=10x-dev`

**Session 1 prompt (Architecture)**:
```
Design the execution policy abstraction for DataServiceClient per WS-DSC seed.
Produce a TDD for the EndpointPolicy protocol and DefaultEndpointPolicy.
Reference the 5 endpoint modules listed in the seed for current-state analysis.
Keep TDD focused: protocol definition, migration strategy, test strategy.
```

**Session 2 prompt (Implementation)**:
```
Implement WS-DSC execution policy per the TDD produced in Session 1.
See the TDD at [path from Session 1 checkpoint].
Start with _policy.py, then refactor simple.py, then remaining endpoints
in order: reconciliation -> export -> insights -> batch.
Run tests after each endpoint migration. Emit checkpoint if not complete.
```

**Session 3 prompt (if needed, QA)**:
```
Complete WS-DSC. See checkpoint in MEMORY.md.
Migrate remaining endpoints, verify client.py composition,
run integration tests. Update MEMORY.md when done.
```

**@-references**:
- Session 1: `@PROMPT_0.md`, `@WS-DSC.md`
- Session 2: `@PROMPT_0.md`, `@WS-DSC.md`, `@<TDD-path-from-session-1>`
- Session 3: `@PROMPT_0.md`, `@WS-DSC.md`

**Agent routing**: Full 10x-dev flow. Session 1 = architect phase (TDD).
Session 2 = principal-engineer phase (implementation). Session 3 = QA/completion
if needed. Pythia routes at session start.

**Key source files to front-load in architect prompt** (not @-referenced, but
mentioned so the architect reads them):
```
src/autom8_asana/clients/data/_endpoints/simple.py (234 LOC)
src/autom8_asana/clients/data/_endpoints/batch.py (310 LOC)
src/autom8_asana/clients/data/_retry.py (191 LOC)
```

---

### WS-DFEX (DataFrame Extraction + Holder Registry) -- 2 Sessions

**Type**: MODULE-hygiene
**Launch command**: `/start "WS-DFEX: DataFrame extraction + holder registry" --complexity=MODULE`

**Session 1 prompt (Part A: DataFrame extraction)**:
```
Execute WS-DFEX Part A: Extract build_dataframe() from models to DataFrameService.
Follow the seed file steps. Audit all callers, update one first, then batch.
Verify no dataframes imports remain in models/project.py or models/section.py.
```

**Session 2 prompt (Part B: Holder registry)**:
```
Execute WS-DFEX Part B: Implement holder type registry in persistence.
See MEMORY.md for Part A completion status.
Follow the seed file steps. Add completeness test.
Run full suite. Update MEMORY.md when done.
```

**@-references (2 files each session)**:
1. `@PROMPT_0.md`
2. `@WS-DFEX.md`

**Agent routing**: Principal-engineer direct for both parts. The seed file IS
the design -- no separate architect phase needed for hygiene-level extraction.

---

### WS-CLASS (Classification Rules) -- 0-1 Sessions

**Type**: PATCH-hygiene (conditional)
**Launch command**: `/start "WS-CLASS: Classification rule externalization" --complexity=PATCH`

**Gate check** (resolve BEFORE creating session):
```bash
cd /Users/tomtenuta/Code/autom8y-asana
git log --oneline --follow -p src/autom8_asana/models/business/activity.py \
  | grep -A2 -B2 "OFFER_SECTIONS\|UNIT_SECTIONS"
```

**If EXECUTE**: Single session, PATCH complexity. @-ref PROMPT_0 + WS-CLASS.
**If SKIP**: No session needed. Write to MEMORY.md: "WS-CLASS: SKIPPED, classification rules stable per U-002 (N changes in 6 months)"

---

### WS-QUERY (Query Engine Decoupling) -- 2 Sessions

**Type**: MODULE-10x
**Launch command**: `/start "WS-QUERY: Query engine decoupling" --complexity=MODULE --rite=10x-dev`

**Session 1 prompt (Architecture + Implementation)**:
```
Design and implement the DataFrameProvider protocol for query engine decoupling
per WS-QUERY seed. This is a focused protocol extraction -- the TDD can be
lightweight (protocol definition + DI wiring). Implement in same session if
architect phase completes quickly.
```

**Session 2 prompt (Completion + QA)**:
```
Complete WS-QUERY. See MEMORY.md checkpoint.
Update API route DI, write mock-provider test, run full suite.
Update MEMORY.md when done.
```

**@-references**: `@PROMPT_0.md`, `@WS-QUERY.md`

**Dependency note**: Best after WS-DFEX. Include in Session 1 prompt:
"WS-DFEX has been completed -- DataFrameService now owns build_dataframe().
Use the clean service boundary for the DataFrameProvider protocol."

---

### WS-HYGIENE (Cross-Rite Referrals) -- 2-3 Sessions

**Type**: Mixed PATCH/MODULE-hygiene
**Launch command**: `/start "WS-HYGIENE: Cross-rite hygiene referrals" --complexity=MODULE`

**Session 1 prompt (XR-006, XR-003, XR-004)**:
```
Address hygiene referrals per WS-HYGIENE seed.
Start with XR-ARCH-006 (verify test failures, 30 min).
Then XR-ARCH-003 (private API elimination, 0.5 day).
Then XR-ARCH-004 (InsightsProvider protocol, 0.5 day).
Emit checkpoint.
```

**Session 2 prompt (XR-005, optionally XR-001)**:
```
Continue WS-HYGIENE. See MEMORY.md for completed items.
Execute XR-ARCH-005 (MetricsEmitter protocol, eliminate Cycle 5).
If time permits, begin XR-ARCH-001 (directory reorg).
```

**@-references**: `@PROMPT_0.md`, `@WS-HYGIENE.md`

**Batching rationale**: XR-003, XR-004, XR-005 are all protocol extractions
(similar pattern). Grouping them in adjacent sessions enables pattern reuse
in the agent's working memory.

---

### WS-DEBT (v1 Sunset Audit) -- 1 Session

**Type**: PATCH-debt
**Launch command**: `/start "WS-DEBT: v1 sunset consumer audit" --complexity=PATCH --rite=debt-triage`

**Session prompt**:
```
Audit v1 query API consumers per WS-DEBT seed.
Code audit first (Step 1), then document findings.
Traffic audit (Step 2) requires operational access -- document what you
CAN determine from code, note what requires CloudWatch access.
Make the remove-or-migrate decision based on available evidence.
Update D-002 in debt ledger and MEMORY.md.
```

**@-references**: `@PROMPT_0.md`, `@WS-DEBT.md`

**Note**: This session likely needs the debt-triage rite, which has a different
agent set. If debt-triage agents are not materialized, run as native-mode
investigation without session orchestration.

---

## 3. Context Flow Diagram

```
                        HUB THREAD (your terminal)
                        ==========================
                        Owns: MEMORY.md, PROMPT_0.md, DEPENDENCY-GRAPH.md
                        Tracks: phase gates, session completion, unknown resolution
                        Does NOT: execute workstream code

         ┌──────────────────────┼──────────────────────┐
         |                      |                      |
    ┌────v─────┐          ┌────v─────┐          ┌────v─────┐
    | Worktree | parallel | Worktree | parallel | Worktree |
    | Session  | ~~~~~~~ >| Session  | ~~~~~~~ >| Session  |
    | WS-SYSCTX|          | WS-DSC   |          |WS-HYGIENE|
    └────┬─────┘          └────┬─────┘          └────┬─────┘
         |                      |                      |
    reads:                 reads:                 reads:
    - CLAUDE.md            - CLAUDE.md            - CLAUDE.md
    - MEMORY.md            - MEMORY.md            - MEMORY.md
    - PROMPT_0.md          - PROMPT_0.md          - PROMPT_0.md
    - WS-SYSCTX.md        - WS-DSC.md            - WS-HYGIENE.md
         |                      |                      |
    writes:                writes:                writes:
    - Code changes         - TDD artifact         - Code changes
    - Test results         - Code changes         - Test results
         |                      |                      |
    on completion:         on completion:          on completion:
    -> MEMORY.md           -> MEMORY.md            -> MEMORY.md
    -> merge to main       -> merge to main        -> merge to main
    -> signal hub          -> signal hub            -> signal hub

CONTEXT FLOW:
=============
  Hub -> Session:   PROMPT_0 guardrails + WS-specific seed + MEMORY.md state
  Session -> Disk:  Code changes, test results, TDD artifacts (in worktree)
  Session -> Hub:   MEMORY.md checkpoint/completion entry
  Hub -> Hub:       Phase gate evaluation, next session selection
  Session -> Main:  Git merge of worktree branch
```

### Information Flow Rules

1. **Hub -> Session**: Front-load via @-references at session start. Two files
   maximum per session (PROMPT_0 + workstream seed). Additional context flows
   through MEMORY.md (auto-injected).

2. **Session -> MEMORY.md**: Checkpoints and completion entries. Written at
   session end (via `/wrap` or manual update). NEVER during session execution
   (avoids mid-session file conflicts).

3. **Session -> Git**: All code changes stay in worktree branch until session
   completes. Merge to main happens between sessions, never during.

4. **Hub -> Next Session**: The hub reads MEMORY.md + checks git log to
   determine what completed, then crafts the next session's prompt with
   appropriate context ("WS-SYSCTX completed, Cycle 4 eliminated").

---

## 4. Parallelization Map with Scope Boundary Contracts

### Parallelization Windows

```
WEEK 1:  [WS-QW] ........................ (sequential, first)
          RESOLVE UNKNOWNS (U-002, U-003, U-006, U-007, U-008)

WEEK 2:  [WS-SYSCTX S1] || [WS-DSC S1] || [WS-HYGIENE S1]
          ^^^^^^^^^^^^      ^^^^^^^^^^      ^^^^^^^^^^^^^^
          core/             clients/data/   various (protocol
          system_context.py _endpoints/     extractions in
                            _policy.py      models/, cache/,
                                            dataframes/)

WEEK 3:  [WS-SYSCTX S2] || [WS-DSC S2] || [WS-HYGIENE S2] || [WS-DEBT]
                            ^^^^^^^^^^
                            Continues
                            endpoint
                            migration

WEEK 4:  [WS-DFEX S1]   || [WS-DSC S3] || [WS-CLASS]
          ^^^^^^^^^^^^
          models/ ->
          services/

WEEK 5:  [WS-DFEX S2]   || [WS-QUERY S1]
          persistence/      query/

WEEK 6:  [WS-QUERY S2]
```

### Scope Boundary Contracts

These contracts prevent file-level conflicts between parallel sessions.

| Session A | Session B | Boundary Contract |
|-----------|-----------|-------------------|
| WS-SYSCTX | WS-DSC | **No overlap.** SYSCTX touches `core/system_context.py` + registration calls in singleton modules. DSC touches `clients/data/_endpoints/` and `clients/data/_policy.py` (new). Zero shared files. |
| WS-SYSCTX | WS-HYGIENE | **Potential overlap on `dataframes/models/registry.py`.** SYSCTX adds `register_reset()` call. WS-HYGIENE XR-003 adds `on_schema_change` callback. **Resolution**: Run XR-003 AFTER WS-SYSCTX singleton 1 (SchemaRegistry) migrates. Or accept a merge conflict on `registry.py` (additive-only changes, trivially resolvable). |
| WS-DSC | WS-HYGIENE | **No overlap.** DSC is scoped to `clients/data/`. HYGIENE referrals touch `dataframes/`, `models/business/`, `cache/`, `automation/`. |
| WS-DSC | WS-DEBT | **No overlap.** DSC modifies client internals. DEBT audits `api/routes/query.py` and debt ledger docs. |
| WS-DFEX | WS-QUERY | **Sequential, not parallel.** Both touch `services/` and the query-to-dataframe boundary. WS-QUERY depends on WS-DFEX producing clean DataFrameService interfaces. |
| WS-DFEX | WS-HYGIENE | **Potential overlap on `models/business/`.** DFEX removes `build_dataframe()` from model files. WS-HYGIENE XR-004 modifies `models/business/business.py` TYPE_CHECKING imports. **Resolution**: Run XR-004 after WS-DFEX Part A completes, or in a later HYGIENE session. |

### Maximum Safe Parallelism

**3 concurrent worktree sessions** is the practical maximum for this initiative:

1. Core/infrastructure track: WS-SYSCTX or WS-DFEX
2. Client track: WS-DSC
3. Cross-cutting track: WS-HYGIENE or WS-DEBT

Beyond 3, the user's ability to monitor and merge becomes the bottleneck, not
file conflicts.

---

## 5. MEMORY.md Write Protocol

### Principles

1. **Write at session boundaries, not during.** A session writes to MEMORY.md
   at wrap time, never mid-execution. This prevents merge conflicts between
   parallel sessions.

2. **Checkpoints go to MEMORY.md only between sessions.** If a multi-session
   workstream needs a checkpoint, the user writes it to MEMORY.md after the
   worktree merges to main, before starting the next session.

3. **Append-only within a section.** Each workstream gets its own subsection.
   Parallel sessions append to different subsections, avoiding conflicts.

4. **Hub thread owns MEMORY.md writes.** Sessions produce checkpoint text in
   their final output. The hub thread (user's main terminal) copies it into
   MEMORY.md. This serializes all writes through one actor.

### Write Schema Per Session Type

**Single-session workstream (WS-QW, WS-CLASS, WS-DEBT)**:
```markdown
## Completed Work (WS-{ID}) [{date}]
- WS-{ID}: {outcome} [date]
  - {item}: {result}
  - {item}: {result}
  - Test status: {pass}/{total}
```

**Multi-session workstream checkpoint (mid-stream)**:
```markdown
## Checkpoint WS-{ID} [{date}]
Completed: {list of completed steps}
Remaining: {list of remaining steps}
Decisions: {key decisions with brief rationale}
Artifacts: {paths to TDDs, ADRs, etc.}
Test status: {pass count} passed
Branch: {worktree branch name if applicable}
```

**Multi-session workstream completion**:
```markdown
## Completed Work (WS-{ID}) [{date}]
- WS-{ID}: {summary} DONE [date]
  - {recommendation}: {outcome}
  - Cycles eliminated: {list}
  - Test status: {pass}/{total}
  - Key files: {most important changed files}
```

**Unknown resolution**:
```markdown
## Unknown Resolutions [{date}]
- U-{NNN}: {resolution}. Decision: {action taken or skipped}
```

### Merge Conflict Prevention

The hub thread should batch MEMORY.md updates between parallel session merges:

```
1. Session A completes -> merge A's worktree to main
2. Session B completes -> merge B's worktree to main
3. Hub thread updates MEMORY.md with both A and B completions
4. Commit MEMORY.md update
5. Start next sessions (which will see updated MEMORY.md)
```

If a session absolutely must write MEMORY.md itself (e.g., unknown resolution
during WS-QW), it writes ONLY to its own subsection heading. Parallel sessions
use different headings, so git merge resolves automatically.

---

## 6. Hub Thread Orchestration Playbook

### Hub Thread Role

The hub thread is your main terminal session. It does NOT run workstream code.
It orchestrates: resolving unknowns, creating worktrees, launching sessions,
monitoring completion, merging results, updating MEMORY.md, and selecting the
next workstream to launch.

### Phase 0: Pre-Flight (30-45 minutes)

**Objective**: Resolve blocking unknowns and establish baseline.

```
Step 1: Load UNKNOWNS-RESOLUTION.md
Step 2: Resolve U-003, U-007, U-002, U-008, U-006 (top 5, ~25 min)
Step 3: Write resolutions to MEMORY.md
Step 4: Resolve U-002 decision -> determines if WS-CLASS executes
Step 5: Run full test suite to confirm 10,552+ baseline
Step 6: Create WS-QW worktree and launch session
```

This can run in the hub thread directly (native mode, no rite needed).

### Phase 1: Foundation (Launch After WS-QW Merges)

```
Step 1: Merge WS-QW worktree to main
Step 2: Update MEMORY.md with WS-QW results
Step 3: Create 2-3 parallel worktrees:
        - /worktree create "ws-sysctx" --rite=hygiene
        - /worktree create "ws-dsc" --rite=10x-dev
        - /worktree create "ws-hygiene" --rite=hygiene  (optional parallel)
Step 4: Launch sessions in each worktree terminal
Step 5: Monitor progress (check git log in worktrees periodically)
Step 6: As each completes:
        - Merge worktree to main
        - Update MEMORY.md
        - Remove worktree
Step 7: When WS-SYSCTX completes, gate check for WS-DFEX readiness
```

### Phase 2: Consolidation (Launch After Phase 1 Core Completes)

```
Step 1: Confirm WS-SYSCTX merged (soft prereq for WS-DFEX)
Step 2: Create worktrees:
        - /worktree create "ws-dfex" --rite=hygiene
        - /worktree create "ws-class" --rite=hygiene  (if U-002 = EXECUTE)
Step 3: Launch sessions
Step 4: WS-DSC may still be running in parallel -- this is safe
Step 5: Monitor and merge as each completes
```

### Phase 3: Evolution (After WS-DFEX Merges)

```
Step 1: Confirm WS-DFEX merged (soft prereq for WS-QUERY)
Step 2: Create worktree:
        - /worktree create "ws-query" --rite=10x-dev
Step 3: Launch session with note: "WS-DFEX completed, use clean service boundary"
Step 4: Monitor and merge
```

### Cross-Rite Work (Slot Into Any Gap)

```
WS-HYGIENE: Split across 2-3 sessions, parallelizable with any phase.
            Launch in gaps between phase transitions.
WS-DEBT:    Single session, any time. Requires debt-triage rite.
            Good candidate for a quiet gap in Week 3.
```

### Hub State Tracking

The hub thread maintains state through a simple checklist. Keep this as a
scratchpad in the hub terminal or in a `.claude/wip/REM-ASANA-ARCH/TRACKER.md`:

```markdown
# REM-ASANA-ARCH Progress Tracker

## Unknowns
- [x] U-003: {result}
- [x] U-007: {result}
- [x] U-002: {EXECUTE|SKIP}
- [x] U-008: {result}
- [x] U-006: {result}
- [ ] U-001: (long-term, not blocking)
- [ ] U-004: (needs operational data)

## Workstreams
- [x] WS-QW: DONE {date} | Branch: merged
- [ ] WS-SYSCTX: IN PROGRESS | Branch: ws-sysctx | Session: 1/2
- [ ] WS-DSC: IN PROGRESS | Branch: ws-dsc | Session: 1/3
- [ ] WS-DFEX: PENDING (after WS-SYSCTX)
- [ ] WS-CLASS: {PENDING|SKIPPED}
- [ ] WS-QUERY: PENDING (after WS-DFEX)
- [ ] WS-HYGIENE: IN PROGRESS | Items: 2/5 done
- [ ] WS-DEBT: PENDING

## Health Score
- Baseline: 68/100
- After Phase 0: ~70/100
- After Phase 1: ~74/100
- After Phase 2: ~78/100
- Target: ~80/100
```

### Session Completion Detection

The hub knows a session is done when:

1. **Worktree has clean git status**: `cd <worktree> && git status --porcelain`
   returns empty (all changes committed).
2. **Session was wrapped**: `/wrap` was invoked in the worktree terminal.
3. **MEMORY.md checkpoint exists**: The session's output includes completion text.

The user merges manually: `cd <main-project> && git merge <worktree-branch>`.

---

## 7. Token Economics Summary

### What Is Expensive

| Concern | Token Cost | Mitigation |
|---------|-----------|------------|
| Deep-dive analysis files (3,122 lines) | ~14,000 per file load | NEVER front-load. Load specific sections only when seed references them. |
| Full PROMPT_0.md in every session | ~900 per session | Acceptable. Guardrails are essential. No trimming. |
| Pythia orchestration overhead | ~3,500 per consultation | For PATCH complexity, skip Pythia. Route to PE directly. |
| Long test suite output | ~2,000-5,000 per run | Use `--tb=short` and `-x` (fail-fast). Avoid `--tb=long` unless debugging. |
| Accumulating conversation history | ~1,000 per turn | Natural session boundaries (1-2 sessions per WS) keep this manageable. |

### What Is Cheap

| Approach | Token Cost | Benefit |
|----------|-----------|---------|
| Seed file per session | ~500-650 | Complete execution spec in minimal tokens |
| MEMORY.md as state bus | ~500 (growing to ~800) | Auto-injected, no @-reference needed |
| CLAUDE.md chain | ~1,500 | Carries project conventions without explicit loading |
| Workstream-scoped prompts | ~100-200 | Tight, specific, no ambiguity |

### What to Trim

1. **MEMORY.md growth**: After this initiative completes, archive the per-workstream
   entries into a summary paragraph. The current ~99 lines will grow to ~150-200
   during the initiative. Compact to ~120 after completion.

2. **Pythia for PATCH work**: 5 of 8 workstreams are hygiene-rite PATCH or MODULE
   where the seed file IS the design. Skip Pythia consultation for these. Save
   ~3,500 tokens per skipped orchestration round.

3. **Architect phase for hygiene MODULE**: WS-SYSCTX, WS-DFEX, WS-HYGIENE all
   have implementation sketches in their seeds. The architect phase adds value
   only for WS-DSC and WS-QUERY (10x-dev rite, where TDD is protocol). Skip
   architect for hygiene MODULE work.

### Effective Token Budget Per Session Type

| Session Type | Initial Context | Agent Overhead | Working Budget |
|-------------|----------------|----------------|----------------|
| PATCH-hygiene | ~5,650 | ~800 (PE only) | ~193K remaining (of 200K) |
| MODULE-hygiene | ~5,650 | ~2,400 (PE + optional architect) | ~192K remaining |
| MODULE-10x | ~5,650 | ~7,000 (Pythia + architect + PE) | ~187K remaining |
| PATCH-debt | ~5,100 | ~800 (investigator) | ~194K remaining |

All session types have ample headroom. Context overflow is not a risk for this
initiative. The constraint is scope discipline, not token budget.

---

## 8. Guardrails Inheritance Strategy

### The 7 Guardrails (from PROMPT_0.md)

These are inviolable across all sessions. They are loaded via `@PROMPT_0.md`
at session start. They do NOT need repeating in individual seed files because
every seed already says "load PROMPT_0.md first."

1. Do NOT decompose SaveSession
2. Do NOT re-open cache divergence (ADR-0067)
3. Do NOT pursue full pipeline consolidation (D-022)
4. Do NOT convert deferred imports wholesale (SI-3)
5. Do NOT modify automation/seeding.py field strategy
6. Run tests after every change (green-to-green)
7. Verify file paths before editing

### Per-Seed "Do NOT" Sections

Each WS seed has its own "Do NOT" section with workstream-specific guardrails.
These are narrower and operational:
- WS-QW: "Do not touch seeding strategy"
- WS-SYSCTX: "Do not move system_context.py out of core/"
- WS-DSC: "Do not change the retry callback factory"
- etc.

These are already embedded in the seed files and do not need separate injection.

### MEMORY.md Carries Implicit Guardrails

The "Closed Items" and "Deferred Items" sections in MEMORY.md serve as implicit
guardrails. Any session inheriting MEMORY.md will see:
- "D-022 CLOSED"
- "SaveSession is a Coordinator -- NOT a god object, do not decompose"
- "SI-3: Circular deps -- deferred"

This is sufficient. Do not duplicate guardrails in session prompts beyond the
@PROMPT_0.md reference.

---

## 9. Session Launch Quick Reference

For each session launch, the user types these lines in the appropriate terminal.

### Pre-Flight (Hub Terminal)
```
# Resolve unknowns (native mode, no session needed)
@.claude/wip/REM-ASANA-ARCH/UNKNOWNS-RESOLUTION.md
Execute U-003, U-007, U-002, U-008, U-006 in order. Write results to MEMORY.md.
```

### WS-QW (Hub Terminal or Worktree)
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-QW.md
/start "WS-QW: Quick Wins" --complexity=PATCH
```

### WS-SYSCTX (Worktree Terminal)
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-SYSCTX.md
/start "WS-SYSCTX: system_context registration pattern" --complexity=MODULE
```

### WS-DSC (Worktree Terminal)
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-DSC.md
/start "WS-DSC: DataServiceClient execution policy" --complexity=MODULE --rite=10x-dev
```

### WS-DFEX (Worktree Terminal)
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-DFEX.md
/start "WS-DFEX: DataFrame extraction + holder registry" --complexity=MODULE
```

### WS-CLASS (Worktree Terminal, if triggered)
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-CLASS.md
/start "WS-CLASS: Classification rule externalization" --complexity=PATCH
```

### WS-QUERY (Worktree Terminal)
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-QUERY.md
/start "WS-QUERY: Query engine decoupling" --complexity=MODULE --rite=10x-dev
```

### WS-HYGIENE (Worktree Terminal)
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-HYGIENE.md
/start "WS-HYGIENE: Cross-rite hygiene referrals" --complexity=MODULE
```

### WS-DEBT (Worktree Terminal)
```
@.claude/wip/REM-ASANA-ARCH/PROMPT_0.md
@.claude/wip/REM-ASANA-ARCH/WS-DEBT.md
/start "WS-DEBT: v1 sunset consumer audit" --complexity=PATCH --rite=debt-triage
```

---

## 10. Failure Modes and Recovery

### Session Context Overflow (Unlikely)

**Symptom**: Agent loses track of what it was doing mid-session.
**Recovery**: Emit checkpoint, start fresh session with checkpoint context.
**Prevention**: Single-workstream scope per session keeps context focused.

### Merge Conflict Between Parallel Worktrees

**Symptom**: `git merge <worktree-branch>` has conflicts.
**Recovery**: Resolve manually. Conflicts are expected to be additive-only
(both sessions adding to different files). The scope boundary contracts above
minimize this.
**Prevention**: Merge sequentially (A then B), not simultaneously. Run tests
after each merge.

### MEMORY.md Grows Too Large

**Symptom**: MEMORY.md exceeds ~200 lines, consuming >1,000 tokens per turn.
**Recovery**: After each phase completes, compact that phase's entries into a
single summary line. Archive detail to a `.claude/wip/REM-ASANA-ARCH/COMPLETED-LOG.md`.
**Prevention**: Use terse checkpoint format. One line per recommendation, not
paragraphs.

### Session Produces Wrong Work (Guardrail Violation)

**Symptom**: Session attempts to decompose SaveSession, re-open cache divergence, etc.
**Recovery**: Abort session. The worktree branch contains no merged changes.
Delete worktree, restart session with explicit guardrail reminder in prompt.
**Prevention**: PROMPT_0.md @-reference at every session start. MEMORY.md
reinforces closed decisions.

### Dependency Violation (Wrong Phase Order)

**Symptom**: WS-QUERY started before WS-DFEX, produces suboptimal interface.
**Recovery**: The dependency is SOFT. WS-QUERY can technically succeed without
WS-DFEX. If the resulting interface is awkward, refactor after both complete.
**Prevention**: Hub thread follows the phase order in Section 6.

---

## Appendix: Why This Architecture Works

### Scope Boundaries > Token Targets

The key insight from prior work on this project: "scope boundaries are the
effective token management lever, not explicit token targets." This architecture
operationalizes that insight:

- Each session has ONE workstream (scope boundary = workstream)
- Each session loads TWO @-referenced files (PROMPT_0 + seed)
- Each seed file is self-contained (100-145 lines, ~500-650 tokens)
- Deep-dive files are NEVER front-loaded (progressive disclosure)
- MEMORY.md carries inter-session state automatically

### Front-Load File Paths, Not Content

Another prior insight: "front-load file paths + deliverable specs in prompts."
The seed files already do this -- they list exact source file paths, step-by-step
instructions, and definition-of-done checklists. The session agent discovers
content by reading those paths, rather than having content injected upfront.

### Natural Session Boundaries

Every workstream has 1-3 sessions, each scoped to a coherent phase:
- Session 1: Design or first batch of changes
- Session 2: Remaining changes or QA
- Session 3: Completion (only for WS-DSC, WS-HYGIENE)

These are natural breakpoints where context debt resets. No session should
exceed ~50 turns (most will be 20-30), keeping conversation history manageable.
