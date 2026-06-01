---
artifact_id: HANDOFF-eunomia-to-10x-dev-asyncio-run-in-sync-async-native-migration-2026-06-01
schema_version: "1.0"
type: handoff
source_rite: eunomia
target_rite: 10x-dev
handoff_type: assessment
priority: medium
blocking: false
altitude: OPERATIONAL
initiative: ci-cd-test-ecosystem-rationalization-asyncio-run-in-sync-async-native-migration
created_at: "2026-06-01T16:00:00Z"
status: in_progress
source_artifacts:
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/spikes/HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/PLAN-ci-cd-test-ecosystem-rationalization-2026-06-01.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/pipeline-inventory-2026-06-01.md
  - /Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/test-inventory-2026-06-01.md
evidence_grade: strong
---

## Premise

Seven unquarantined test files containing 41 `asyncio.run`-in-sync-`def` call sites carry the same SIGKILL exposure class as the already-quarantined `test_workflow_handler.py`; eunomia confirms the root fix is async-native production code plus `async def` test migration, and routes this work to 10x-dev as parallel to (not a replacement for) the FROZEN `worker_isolated` quarantine.

## Evidence

- `.sos/wip/eunomia/test-inventory-2026-06-01.md:189-204` — ASSESS-5 "Full asyncio.run-in-handler Risk Family" table enumerates the 8-file xdist risk family (1 quarantined + 7 unquarantined).
- `.sos/wip/eunomia/test-inventory-2026-06-01.md:196-202` — Per-file call-site counts for the 7 unquarantined files:
  - `tests/unit/patterns/test_async_method.py` — 12 sites
  - `tests/unit/lifecycle/test_lifecycle_observation_contracts.py` — 10 sites
  - `tests/unit/models/business/test_seeder.py` — 14 sites
  - `tests/unit/lifecycle/test_observation.py` — 2 sites
  - `tests/unit/dataframes/test_freshness_verification_recency.py` — 2 sites
  - `tests/unit/dataframes/test_public_api.py` — 1 site (sync path test)
  - `tests/unit/models/business/test_resolution.py` — 2 sites (commented; structurally impossible)
- `.sos/wip/eunomia/test-inventory-2026-06-01.md:379-380` — "asyncio.run call sites (unquarantined) | 41 calls across 7 files".
- `.sos/wip/eunomia/test-inventory-2026-06-01.md:181-187` — Quarantined file `tests/unit/lambda_handlers/test_workflow_handler.py`; root = handler runs `asyncio.run` internally at production-code `workflow_handler.py:96-97`; "Not fixable at test level without restructuring the production handler to be async-native."
- `.sos/wip/eunomia/test-inventory-2026-06-01.md:206` — Risk-profile distinction: patterns/lifecycle/seeder/dataframes test async-to-sync bridges or pure async called via `asyncio.run`; they do not spawn nested loops/threads like the handler, but remain "structurally non-idiomatic under pytest-asyncio auto mode".
- `.sos/wip/eunomia/test-inventory-2026-06-01.md:208-210` — Files confirmed non-risky at current marker level: `test_resolution.py` (commented out) and `tests/benchmarks/bench_batch_operations.py` (excluded from normal runs).
- `.sos/wip/eunomia/test-inventory-2026-06-01.md:410-411` — ASSESS-5 root fix prescription: "convert production code to async-native where possible; migrate tests to `async def` + pytest-asyncio where the production code is async. The quarantine-as-permanent-design for `test_workflow_handler.py` is the technical debt embodiment."
- `.sos/wip/eunomia/pipeline-inventory-2026-06-01.md:243-251` — CI structure: `test.yml:216` runs `workflow-handler-isolated` job with `continue-on-error: true`; `pyproject.toml:112` documents the quarantine comment ("Remove when the production handler / test harness drops the nested-loop pattern."); no formalized promotion-from-quarantine criteria, no issue/ticket reference — indefinite quarantine.
- `.sos/wip/eunomia/pipeline-inventory-2026-06-01.md:468` — ASSESS-5 mapping: "CI structure is correct containment; root fix requires production handler code change."
- `.sos/wip/eunomia/PLAN-ci-cd-test-ecosystem-rationalization-2026-06-01.md:12` — PT-α verdict applied: ASSESS-1 root = branch-protection-required-check-gap; ASSESS-5 (asyncio risk family) deferred from PLAN scope to this assessment handoff.
- `.ledge/spikes/HANDOFF-10x-dev-to-eunomia-ci-cd-test-ecosystem-rationalization-2026-06-01.md:73-77` — Parent B7 item: "workflow_handler xdist crash quarantine — symptom containment, not root resolution. … Root (asyncio.run-in-handler pattern) acknowledged in memory but not fixed." Parent open question: "How many other tests carry the same risk (asyncio.run inside handler-style code under xdist)?" — answered here: 7 files, 41 sites.

## Recommended actions

10x-dev (parallel workstream — does NOT touch the FROZEN `worker_isolated` quarantine):

1. **Scope confirmation pass** (1 sprint).
   - Read `src/autom8_asana/lambda_handlers/workflow_handler.py:96-97` for the production-handler `asyncio.run` pattern and confirm whether parallel async-native handler scaffolding belongs in this initiative or a separate handler-refactor initiative.
   - Per file in the 7-file unquarantined set, classify each `asyncio.run` site as one of: (a) production code is sync, test bridges to async helper — convert helper to async-native + test to `async def`; (b) production code is already async, test calls via `asyncio.run` — direct migration to `async def` + pytest-asyncio; (c) intentional sync-path coverage — leave as-is, add marker + comment justifying retention.

2. **Per-file migration sprints**, ordered by site density (highest first to retire most risk per sprint):
   - Sprint A: `tests/unit/models/business/test_seeder.py` (14 sites).
   - Sprint B: `tests/unit/patterns/test_async_method.py` (12 sites).
   - Sprint C: `tests/unit/lifecycle/test_lifecycle_observation_contracts.py` (10 sites).
   - Sprint D: `tests/unit/lifecycle/test_observation.py` + `tests/unit/dataframes/test_freshness_verification_recency.py` (2 + 2 sites; bundled).
   - Sprint E: `tests/unit/dataframes/test_public_api.py` (1 site; decide retain-as-sync-path-coverage vs migrate).
   - Sprint F: `tests/unit/models/business/test_resolution.py` (2 commented sites; either delete commented blocks or convert).

3. **Per-sprint deliverable**: one atomic commit per file with (i) production-code async-native conversion if classification (a); (ii) test migration to `async def` + pytest-asyncio; (iii) full local pytest run for that file showing green; (iv) no new `asyncio.run` call site introduced anywhere under `tests/`.

4. **Verification of risk retirement**: after each sprint, re-run `grep -rn "asyncio.run" tests/` and update the running count toward zero. Final state target: 0 unquarantined `asyncio.run`-in-sync-`def` sites across `tests/`.

5. **Coordinate handler refactor separately**: if scope-confirmation pass concludes the production handler at `workflow_handler.py:96-97` needs async-native restructuring to un-quarantine `test_workflow_handler.py`, open a distinct initiative + handoff. That work is downstream of this one and gated on its completion.

**Rollback plan**: each per-file migration is its own atomic commit. If a migrated file flakes in CI or surfaces unanticipated behavior, `git revert <sha>` of the single commit restores the prior `asyncio.run` pattern (which is known-safe under current marker config — no file in this set has fired the SIGKILL in observed history; the risk is structural exposure, not active failure). No cross-file rollback required.

## Out-of-scope

Eunomia explicitly did NOT touch:

1. **`tests/unit/lambda_handlers/test_workflow_handler.py` quarantine**. The `worker_isolated` marker, `xdist_group("workflow_handler")`, the `continue-on-error: true` job at `test.yml:216`, and the `pyproject.toml:112` quarantine comment remain FROZEN. Do NOT un-quarantine as part of this initiative.
2. **The production `workflow_handler.py:96-97` `asyncio.run` call site itself**. Its restructuring is downstream of this initiative and requires its own scoping; eunomia routed only the test-level + non-handler production-code work here.
3. **`tests/unit/models/business/test_resolution.py` commented sites** and **`tests/benchmarks/bench_batch_operations.py`** — already classified as non-risky at current marker level (`test-inventory-2026-06-01.md:208-210`); they appear in Sprint F only for cleanup hygiene, not risk retirement.
4. **CI workflow file changes** (`test.yml`, `satellite-ci-reusable.yml`). The CI containment structure is correct (`pipeline-inventory-2026-06-01.md:468`); no CI surgery is required for this work.
5. **Promotion-from-quarantine criteria formalization** for `test_workflow_handler.py`. That belongs with the downstream handler-refactor initiative, not here.

## Acceptance criteria

Definition-of-done for 10x-dev:

- [ ] Scope-confirmation pass complete: each of the 7 unquarantined files has a classification (a/b/c) recorded in the per-sprint plan.
- [ ] All 41 `asyncio.run`-in-sync-`def` call sites across the 7 files are either (i) migrated to `async def` + pytest-asyncio, or (ii) retained with explicit justifying comment + marker (classification c only).
- [ ] `grep -rn "asyncio.run" tests/ | grep -v test_workflow_handler.py | grep -v bench_` returns zero hits (or only classification-c retained sites with adjacent justifying comment).
- [ ] No production-code asyncio.run nested-loop pattern introduced; any production-code async-native conversion is verified by direct unit test of the converted function.
- [ ] Full `tests/` pytest run (PR-mode marker set per `test.yml:64`) green across all migrated files; no new flakes introduced; xdist execution under coverage memory pressure does not surface SIGKILL on any migrated file across 3 consecutive CI runs.
- [ ] `test_workflow_handler.py` quarantine status, `worker_isolated` marker, `xdist_group("workflow_handler")`, `pyproject.toml:112` comment, and `test.yml:216` `continue-on-error: true` job are byte-identical to pre-initiative state (verifiable by `git diff <base>..HEAD -- tests/unit/lambda_handlers/test_workflow_handler.py pyproject.toml .github/workflows/test.yml`).
- [ ] Per-sprint atomic-commit discipline: one file migration = one commit, independently revertible.
- [ ] If handler-refactor scope was confirmed in step 1, a separate downstream initiative + handoff is opened referencing this artifact_id.

## Sprint outcomes (running log)

### Sprint-1 — 2026-06-01 — file #1 `tests/unit/lifecycle/test_observation.py` (2 sites, LOW)

- **Status**: `migration-landed` (PR open; CI in flight; pending review + merge). Handoff status remains `in_progress` per per-sprint-atomic-commit discipline.
- **PR**: https://github.com/autom8y/autom8y-asana/pull/79 (state: OPEN, mergeable: MERGEABLE, +23/−5 lines, 2 atomic commits: `b14feea1` code + `18de6e26` docs).
- **Sites migrated**: 2 of 41 (lifecycle/test_observation.py:235, 244 — `TestStageTransitionEmitter.test_emit_calls_store_append`, `test_emit_swallows_store_exception`).
- **Production source diff**: 0 bytes (`git diff main..HEAD -- src/`). Production interface `src/autom8_asana/lifecycle/observation.py:160` (`async def emit`) untouched per DoD.
- **Canonical pattern**: 6-rule mechanical transform codified in `.know/test-coverage.md:131-148` + intentional `asyncio.run` pin catalog.
- **Pattern validation**: STRONG — same production-interface contract is shared with file #4, transform mechanics applied without deviation, harness picks up async-native discovery via `asyncio_mode = "auto"` without per-test decoration.
- **Residual QA defect (sprint-2 carry-forward)**: `.know/test-coverage.md:146` mis-cites the intentional-pin path as `tests/unit/lifecycle/test_freshness_verification_recency.py:736-760`; canonical path is `tests/unit/dataframes/test_freshness_verification_recency.py:736-760` (file lives in `dataframes/`, verified via `find`). Docs-only correction; non-blocking; fold into sprint-2 docs commit (one-line edit).
- **Sprint-2 readiness**: GREEN — file #4 `tests/unit/lifecycle/test_lifecycle_observation_contracts.py` (10 sites, MED) can reuse the validated recipe (same `StageTransitionEmitter.emit` production target; same 6-rule transform; mechanical replication × 5).
- **Verdict artifact**: `.ledge/decisions/SPRINT-VERDICT-10x-dev-b7-sprint-1-2026-06-01.md`.

**Site-retirement progress**: 2 of 41 migrated (4.9%). Remaining unquarantined non-benchmark sites under `tests/`: 43.

### Sprint-2 — 2026-06-01 — file #4 `tests/unit/lifecycle/test_lifecycle_observation_contracts.py` (10 sites, MED)

- **Status**: `migration-landed` (PR open; CI in flight; pending review + merge). Handoff status remains `in_progress` per per-sprint-atomic-commit discipline.
- **PR**: https://github.com/autom8y/autom8y-asana/pull/80 (state: OPEN, mergeable: MERGEABLE, +19/−20 lines, 1 atomic commit: `b8680ba1`).
- **Sites migrated**: 10 of 41 (file #4 — 7 sites against `StageTransitionEmitter.emit` for LO-06 / LO-07 x2 / LO-20 x4 and 3 sites against `LifecycleWebhookDispatcher.handle_event` for LO-18 x2 / LO-19 x2).
- **Production source diff**: 0 bytes (`gh pr diff 80 --name-only` returns single test file). Production interfaces `src/autom8_asana/lifecycle/observation.py:160` (`async def emit`) + `src/autom8_asana/lifecycle/webhook_dispatcher.py:106` (`async def handle_event`) untouched per DoD.
- **Pattern fidelity**: STRONG — 6-rule canonical transform from `.know/test-coverage.md:131-148` applied without modification; no edge cases discovered; multi-interface (2 distinct async production targets) generalization confirmed.
- **Test ID collection parity**: 42-line pytest collection-only output (40 test IDs + 2 collection-header lines) identical pre/post — no silent test loss.
- **Sprint-1 docs carry-forward resolution**: working-tree inspection at `.know/test-coverage.md:146` shows the canonical `tests/unit/dataframes/test_freshness_verification_recency.py:736-760` citation is already in place; the sprint-1 verdict's reading of the diff was a misread. No sprint-2 docs commit was required and none was made. Carry-forward is closed.
- **Sprint-3 readiness**: GREEN with HIGH-complexity advisory — file #5 `tests/unit/patterns/test_async_method.py` (12 sites total; 11 of 12 migrate; preserve pin at line 92 for `SyncInAsyncContextError` guard test; HIGH complexity due to descriptor-class pattern).
- **Verdict artifact**: `.ledge/decisions/SPRINT-VERDICT-10x-dev-b7-sprint-2-2026-06-01.md`.

**Site-retirement progress (cumulative)**: 12 of 41 migrated (29.3%). Remaining unquarantined non-benchmark sites under `tests/`: 33.

### Sprint-3 — 2026-06-01 — file #5 `tests/unit/patterns/test_async_method.py` (12 sites, HIGH) — **HALTED**

- **Status**: `halted` (no commits, no PR, no `src/` diff, no test diff). Branch `10x-dev-b7-sprint-3-asyncio-async-method-descriptor-2026-06-01` HEAD byte-identical to `main` HEAD (`git rev-list --count main..HEAD` = 0). Handoff status remains `in_progress` per per-sprint-atomic-commit discipline.
- **PR**: none opened (nothing to push; no PR to create).
- **HALT decision rationale**: the load-bearing pin at `tests/unit/patterns/test_async_method.py:92` (`asyncio.run(async_caller())` inside `test_sync_in_async_context_raises`) exercises the production-code `SyncInAsyncContextError` guard. Migrating the surrounding test to `async def` + `await` would mean the test body is already inside a running event loop, inverting the test's contract (the guard would never fire; the test would pass for the wrong reason). The sprint-2 verdict's HIGH-complexity advisory mandated pair-review attestation on descriptor-class sites as a precondition; the attestation surface was not satisfied at execution time. Default-to-refuted discipline routed the work to HALT rather than to a single-set-of-eyes commit.
- **Pin-preserve verdict**: STRONG — `tests/unit/patterns/test_async_method.py:92` is byte-identical to pre-initiative state; no migration path through which the guard test could have been inverted in this sprint.
- **Pattern fidelity**: STRONG-for-HALT (Rule 6 strict application at the highest possible altitude); UNKNOWN-for-descriptor-primitive (the canonical pattern remains untested against the `@async_method` descriptor; sprint-4 close-out cannot claim cross-primitive generalization at descriptor scope until that work lands).
- **Sites migrated**: 0 of 41 in this sprint; cumulative unchanged at 12 of 41 (29.3%).
- **Sprint-4 readiness**: GREEN with HIGHEST-complexity advisory + mandatory pair-review on 5 with-patch-nested sites — file #6 `tests/unit/models/business/test_seeder.py` (14 sites total; 9 non-nested Rule-2 sites at lines 269, 305, 327, 359, 375, 398, 414, 444, 459 + 5 with-patch + AsyncMock-nested sites at lines 491, 549, 600, 620, 642). Recommend pair-review attestation on the with-patch-nested batch as a separate atomic commit within the sprint-4 PR.
- **Deferred forward**: file #5 (11 of 12 migration-eligible sites + line-92 docs-catalog increment) is deferred either to a re-attempted sprint-3 in parallel with sprint-4 (with explicit descriptor-class pair-review attestation), or to a later sprint slot after file #6 lands.
- **Verdict artifact**: `.ledge/decisions/SPRINT-VERDICT-10x-dev-b7-sprint-3-2026-06-01.md`.

**Site-retirement progress (cumulative)**: 12 of 41 migrated (29.3%, unchanged). Remaining unquarantined non-benchmark sites under `tests/`: 33 (unchanged).

### Handoff completion criterion

Status flips `in_progress → completed` only after all per-file sprints land (file #5 async_method 11 sites + file #6 seeder 14 sites + file #7 public_api 1 site + residual cleanup of `test_resolution.py` commented sites and `test_freshness_verification_recency.py` second site) OR the initiative is explicitly closed via a closure decision.
