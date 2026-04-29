---
artifact_id: PLAN-followon-ci-2026-04-29
schema_version: "1.0"
type: spec
artifact_type: refactoring-plan
slug: followon-ci-2026-04-29
rite: hygiene
phase: 2-plan
initiative: "Follow-on CI Failure Triage (post PR #41)"
date: 2026-04-29
status: proposed
created_by: architect-enforcer
evidence_grade: MODERATE
self_grade_ceiling_rationale: "self-ref-evidence-grade-rule — architect-enforcer in hygiene rite caps at MODERATE; STRONG would require external rite re-plan."
upstream_smell_report: .ledge/reviews/SMELL-followon-ci-2026-04-29.md
upstream_audit_cite: .ledge/reviews/AUDIT-actual-blockers-2026-04-29.md
authority_boundary:
  may: [plan, recommend, sketch_adr, identify_defer_watch, classify_dispositions]
  may_not: [execute, modify_code, merge]
---

# PLAN — Follow-on CI Failures (2026-04-29)

## §1 Scope and Premise

Three CI failures surfaced on run `25109444280` post PR #41 merge. Per SMELL §F1/§F2/§F3 classifications:
- **F1** Lint Run linting — `independent-pre-existing` (unmasked by C1 format-fix)
- **F2** OpenAPI Spec Drift — `C3-consumer-follow-on` (only true follow-on)
- **F3** Test shard 1/4 — `independent-pre-existing` flake

Per AUDIT §6 Flag #2, all three are out-of-scope of the prior engagement and were surfaced for a follow-up rotation. This PLAN authors per-failure FIX-TO-GREEN | DELETE-AS-OBSOLETE | ACCEPT-WITH-EXPLICIT-FLAG enumeration with recommended dispositions, atomic-commit grammar, sequencing, and Gate A trigger analysis.

Receipt-grammar (F-HYG-CF-A): every claim file:line OR workflow-run URL OR explicit DEFER tag.

## §2 Per-Failure Option Enumeration

### §2.1 — F1: Lint & Type Check / Run linting (27 ruff errors)

**Failure**: 27 I001/F401 violations across 9 files (workflow-run job `73579200300`; SMELL §F1 L33-L41).

**Option FIX-TO-GREEN**:
- Steps:
  1. Run `uv run ruff check --fix .` to auto-resolve I001 (un-sorted imports) — these are mechanical reorderings.
  2. For F401 (unused imports), inspect each: `_exports_helpers.py:25,29,109,144,147,168,171,349,376,401,421` and `exports.py:38,43,44,242,339,383,406,418` plus 5 sibling files (`fleet_query.py:29`, `query.py:17`, `query_service.py:21`, 4 test files). Either delete the unused import OR (rare) add `# noqa: F401` if the import is intentional re-export (verify against `__all__`).
  3. Re-verify: `uv run --no-sources ruff check .` exits 0.
  4. Push branch; confirm `ci / Lint & Type Check` step `Run linting` is SUCCESS.
- Estimated effort: 30-60 min (mostly auto-fix; F401 needs case-by-case review for re-export patterns).
- Risk: **LOW**. ruff `--fix` is idempotent for I001/F401; no semantic changes. Behavior preservation via existing test suite.
- Test verification: `pytest tests/unit/api/test_exports*.py` (4 affected test files); full unit suite re-run.

**Option DELETE-AS-OBSOLETE**:
- Gate change: relax ruff config to ignore I001 + F401 globally (or remove `Run linting` from the workflow's lint job).
- Coverage gap: import-hygiene drift becomes invisible; latent F401 (genuinely-dead code) accumulates; I001 churn produces noisy diffs.
- Mitigation: only viable if the team explicitly decides import-style is not enforced. Negative architectural signal.

**Option ACCEPT-WITH-EXPLICIT-FLAG**:
- ADR location: `.ledge/decisions/ADR-NNN-defer-lint-run-step.md`.
- ADR sketch: "Defer Run linting step until rotation N+1; format-check substep gates style at minimum threshold; the deferred step is restored at deadline 2026-05-29."
- Defer-watch entry shape (per `defer-watch-manifest`):
  ```yaml
  - id: lint-run-linting-debt-2026-04-29
    deferral_rationale: "27 latent I001/F401 violations unmasked when C1 format-fix cleared upstream short-circuit; deferred to allow follow-on hygiene rotation."
    watch_trigger: 2026-05-13  # T+14d
    deadline: 2026-05-29        # T+30d
    escalation_target: hygiene rite Potnia
  ```
- CI config change: add `continue-on-error: true` to the `Run linting` step in `.github/workflows/ci.yml` OR comment-out the step with a TODO ref.

**Recommended disposition**: **FIX-TO-GREEN**. Rationale: (a) auto-fix tooling makes the cost of fixing far below the cost of an ADR + defer-watch entry; (b) each violation is a class-1 hygiene fix per `smell-detection` taxonomy (low-severity, high-fix-value); (c) per `recursive-dogfooding-discipline` Track-A, hygiene rite cannot DELETE its own gate without architectural justification — and there is none here. The format-then-lint short-circuit was *not* deliberate latency-deferral (it was a CI ordering artifact); the lint debt is genuine maintenance debt that should be cleared.

### §2.2 — F2: OpenAPI Spec Drift (C3-consumer follow-on)

**Failure**: `scripts/generate_openapi.py --check` regenerates pre-C3 schema; committed `openapi.json:3736,8356` was hand-edited to `$ref: SuccessResponse`; FastAPI source-of-truth at `src/autom8_asana/api/routes/exports.py:514,546` declares `response_model=None` (verified by direct read at audit time). Workflow-run job `73579200333` (SMELL §F2 L66-L96).

**Root-cause confirmation** (SVR `verification_method: file-read`, sources verified at audit time):
- `src/autom8_asana/api/routes/exports.py:514`: `response_model=None,` (route `post_export_v1`)
- `src/autom8_asana/api/routes/exports.py:546`: `response_model=None,` (route `post_export_api_v1`)
- Both handlers return `Response` (raw fastapi.Response; line 526 + 558 type annotation)
- Both invoke `_format_dataframe_response` from `src/autom8_asana/api/routes/dataframes.py:63` — returns format-negotiated bytes (JSON/CSV/Parquet), NOT a `SuccessResponse`-shaped envelope.

**Architectural assessment**: C3 was incomplete by construction. The committed openapi.json was hand-edited to advertise envelope conformance, but the runtime handlers serialize raw bytes (CSV/Parquet are not envelope-able). The drift CI catches the inconsistency correctly — committed spec lies about runtime behavior.

**Option FIX-TO-GREEN — Sub-A: Bring source-of-truth into alignment**:
- Steps:
  1. Modify `exports.py:514`: change `response_model=None` to `response_model=SuccessResponse[ExportResponse]` OR appropriate model. CAVEAT: this only works if the JSON-format response actually wraps in `{data, meta}` envelope. If the handler returns raw CSV/Parquet bytes for the JSON case too, this is INCORRECT.
  2. Inspect `_format_dataframe_response` at `src/autom8_asana/api/routes/dataframes.py:63` — does the JSON branch wrap in `SuccessResponse`?
     - If YES: declare `response_model=SuccessResponse[…]` on both routes; regenerate spec via `uv run python scripts/generate_openapi.py`; commit.
     - If NO: handler must be modified to wrap JSON responses (this is the architectural change C3 *intended* but did not complete).
  3. Re-verify: `uv run python scripts/generate_openapi.py --check` exits 0.
- Estimated effort: 1-3 hours depending on handler-shape investigation. Includes addition of a contract-conformance test (named in AUDIT §6 Flag #3 as missing test backstop).
- Risk: **MEDIUM-to-HIGH**. This IS the architectural change Gate A authorized at C3 — but the FastAPI source change is the load-bearing edit, not the openapi.json edit. Behavior preservation REQUIRES that the JSON response actually conforms to envelope. If `_format_dataframe_response` returns raw bytes, this is a feature change masquerading as a spec fix.
- Test verification: new contract test asserts `httpx.post('/v1/exports', …)` JSON response has top-level `{data, meta}` keys; existing CSV/Parquet tests must still pass.

**Option FIX-TO-GREEN — Sub-B: Revert C3's openapi.json hand-edits**:
- Steps:
  1. Run `uv run python scripts/generate_openapi.py` to regenerate openapi.json from current FastAPI source (which declares `response_model=None`).
  2. The regenerated spec emits `schema: {}` for the 200 responses (the pre-C3 shape).
  3. Commit the regenerated openapi.json.
  4. The Spectral fleet-envelope-consistency error returns (the C3 problem reappears). The user's Gate A authorization at C3 was contingent on the envelope-wrap going through; reverting it is a regression on that decision.
- Estimated effort: 5 minutes (mechanical regenerate + commit).
- Risk: **LOW** mechanically; **HIGH** product-wise — undoes Gate A-authorized C3 envelope conformance.
- Test verification: `ci / OpenAPI Spec Drift` SUCCESS; `ci / Spectral Fleet Validation` FAILURE returns.

**Option DELETE-AS-OBSOLETE**:
- Gate change: remove `--check` mode from CI (delete the `OpenAPI Spec Drift` job or skip it).
- Coverage gap: spec-source drift becomes invisible; doc-generated openapi.json can diverge from runtime forever.
- Mitigation: only viable if openapi.json is treated as hand-authored documentation, not as a derived artifact. Architectural anti-pattern (the SMELL evidence chain demonstrates exactly the harm).

**Option ACCEPT-WITH-EXPLICIT-FLAG**:
- ADR location: `.ledge/decisions/ADR-NNN-accept-openapi-spec-drift.md`.
- ADR sketch: "Accept committed-vs-generated drift at /api/v1/exports + /v1/exports until source-of-truth alignment lands. Continue-on-error on OpenAPI Spec Drift CI job for one rotation; hard restore at deadline 2026-05-13."
- Defer-watch entry shape:
  ```yaml
  - id: openapi-spec-drift-c3-incomplete-2026-04-29
    deferral_rationale: "C3 envelope-wrap modified openapi.json but not exports.py response_model; full alignment requires either source-fix or runtime-handler envelope-wrap; deferred until follow-on hygiene rotation can attempt Sub-A."
    watch_trigger: 2026-05-06  # T+7d (this is the only true follow-on; tighter watch)
    deadline: 2026-05-13       # T+14d (must not persist; spec lies about runtime)
    escalation_target: hygiene rite Potnia, then user (Gate A re-authorization candidate)
  ```
- CI configuration: `continue-on-error: true` on the OpenAPI Spec Drift job for ONE merge cycle.

**Recommended disposition**: **FIX-TO-GREEN — Sub-A** (with strong Gate A trigger; see §4). Rationale: Sub-B is a regression on C3 Gate A authorization; ACCEPT-WITH-FLAG leaves the spec lying about runtime behavior (architectural anti-pattern); DELETE-AS-OBSOLETE removes the gate that correctly caught the inconsistency. Sub-A IS the work C3 should have done — but it requires user attestation because (a) it touches FastAPI runtime route declarations, (b) the investigation of `_format_dataframe_response` may reveal that the runtime-handler envelope-wrap is NOT in place, escalating from "documentation alignment" to "behavior change." Per `option-enumeration-discipline`, naming this as the recommended disposition while flagging the Gate A trigger preserves the user's authority over the architectural decision. **If `_format_dataframe_response` JSON branch already returns envelope-shape bytes, Sub-A is mechanical (response_model=SuccessResponse[…] declaration only) and Gate A can be a thin attestation rather than a re-decision.**

### §2.3 — F3: Test shard 1/4 wall-clock flake

**Failure**: `test_session_track_100_entities` asserted `<400ms`, observed `1091.7ms` (workflow-run job `73579221418`; SMELL §F3 L100-L141). Test invokes `SaveSession.track()` over 100 in-memory `Task` objects; zero source/test churn in failure window; sibling wall-clock test passed → CI runner variance, not regression.

**Option FIX-TO-GREEN — Sub-A: Optimize the persistence code path**:
- Steps:
  1. Profile `SaveSession.track` over 100 in-memory `Task` objects.
  2. Identify hot loop (likely per-entity I/O setup, lock acquisition, or in-memory journal append).
  3. Optimize until p95 elapsed < 400ms across 50 CI runs.
- Estimated effort: 4-12 hours (includes profiling, optimization, regression validation).
- Risk: **MEDIUM-to-HIGH**. Touches persistence-package internals; behavior preservation requires full test suite + adversarial flake re-runs.
- Test verification: 50-run loop on CI runner showing p95 < 400ms.
- Out-of-rite: This is performance engineering — `/sre` or `/10x-dev` rite ownership, NOT hygiene.

**Option FIX-TO-GREEN — Sub-B: Relax threshold to match observed CI distribution**:
- Steps:
  1. Edit `tests/validation/persistence/test_performance.py:41` constant `HARD_TRACKING_100_ENTITIES_MS = 200` → `1500` (or `750` with `* 2` doubling logic kept).
  2. Update inline comment to record observed CI variance and rationale.
- Estimated effort: 5 minutes mechanical + ADR-sketch authorship.
- Risk: **LOW** mechanically; **MEDIUM** semantically — relaxing a perf assertion erodes its detection power for genuine regressions.
- Test verification: re-run the test 10x on CI to confirm new threshold holds.

**Option DELETE-AS-OBSOLETE**:
- Steps: remove the wall-clock assertion at `test_performance.py:366`; rely on functional correctness only.
- Coverage gap: zero perf regression detection at this surface.
- Mitigation: replace with a relative-perf check (e.g., compare 100-entity case to 10-entity case ratio) or move perf checks to a separate non-blocking job.

**Option ACCEPT-WITH-EXPLICIT-FLAG**:
- ADR location: `.ledge/decisions/ADR-NNN-relax-persistence-perf-threshold.md`.
- ADR sketch: "Wall-clock perf assertions on shared CI runners are inherently flaky due to runner variance (observed 2.7x slower at sha c1faac00 vs nominal). Relax threshold from 200ms (×2 = 400ms ceiling) to 750ms (×2 = 1500ms ceiling) reflecting empirical p99 of CI distribution; revisit when persistence-package latency budget gets a real SLO."
- Defer-watch entry shape:
  ```yaml
  - id: persistence-perf-wall-clock-flake-2026-04-29
    deferral_rationale: "Wall-clock CI perf assertion fragile under runner variance; threshold relaxed pending /sre or /10x-dev rite ownership of persistence latency SLO."
    watch_trigger: 2026-07-29  # T+90d
    deadline: 2026-10-29       # T+180d
    escalation_target: /sre or /10x-dev rite Potnia (perf optimization owner)
  ```
- CI configuration: alternative — mark test as `@pytest.mark.flaky(reruns=3)` with `pytest-rerunfailures`.

**Recommended disposition**: **ACCEPT-WITH-EXPLICIT-FLAG** (relax threshold + ADR + defer-watch). Rationale: (a) Sub-A optimization is out-of-rite (perf engineering = /sre or /10x-dev); (b) Sub-B raw threshold-relax without ADR is undocumented threshold-drift; (c) DELETE removes signal entirely. ACCEPT-WITH-FLAG is the architecturally honest disposition: name the fragility, document the runner-variance reality, defer-watch escalates to perf-owning rite. Triggers Gate A (ADR-authoring is a design decision; see §4).

## §3 Atomic Commit Plan

| Order | Failure | Commit Subject | Files Modified | Type | Rollback |
|---|---|---|---|---|---|
| 1 | F2 | `fix(api): align exports.py response_model with openapi.json envelope shape` | `src/autom8_asana/api/routes/exports.py:514,546`; `docs/api-reference/openapi.json` (regenerated); new contract test `tests/unit/api/test_exports_envelope_contract.py` | fix | `git revert` single commit; restores `response_model=None` and pre-C3 spec |
| 2 | F1 | `style: ruff --fix I001 + remove F401 unused imports across exports surface` | 9 files per SMELL §F1 L42-L52 | style | `git revert` single commit; ruff `--fix` is idempotent so revert is clean |
| 3 | F3 | `test(persistence): relax HARD_TRACKING_100_ENTITIES_MS to reflect CI runner variance` | `tests/validation/persistence/test_performance.py:41`; new ADR at `.ledge/decisions/ADR-NNN-relax-persistence-perf-threshold.md`; new defer-watch entry | test | `git revert` single commit; threshold restoration trivial |

Sequence rationale (per `behavior-preservation` MUST-Preserve discipline + risk ordering):
- **F2 first**: this is the only true follow-on AND the only failure that, if not fixed, persists drift on next merge (spec lies about runtime). Fixing it first ensures the merge cycle does not bake-in the inconsistency.
- **F1 second**: independent and mechanical; can run after F2 lands.
- **F3 third**: ADR authoring is design-decision authoring; sequencing it last lets the F1/F2 verification empirically confirm CI runner behavior before threshold is calibrated.

**Inter-commit dependencies**: NONE structurally. F2 is independent of F1 (different files, different gates). F3 is independent of F1+F2 (test-only file). However, recommended sequence (F2→F1→F3) preserves rollback granularity.

**Rollback points**:
- After commit 1 (F2): `ci / OpenAPI Spec Drift` should be SUCCESS; `ci / Spectral Fleet Validation` should remain SUCCESS. If either fails, single-commit revert.
- After commit 2 (F1): `ci / Lint & Type Check Run linting` should be SUCCESS. Single-commit revert if regression.
- After commit 3 (F3): `ci / Test (shard 1/4)` should be stably green over 5 consecutive runs. If still flaky after threshold relax, escalate to defer-watch entry.

## §4 Risk Matrix and Gate A Triggers

| Failure | Disposition | Blast Radius | Likelihood Recurrence | Effort | Gate A Trigger | Trigger Reason |
|---|---|---|---|---|---|---|
| F1 | FIX-TO-GREEN | LOW (style-only; 9 files; ~30 LoC delta of import order + deletions) | LOW | LOW (30-60min) | **NO** | Below 20-LoC threshold per failure file; auto-fix tooling preserves behavior; no public-API touch |
| F2 | FIX-TO-GREEN Sub-A | MEDIUM (FastAPI route declaration; openapi.json regeneration; new contract test) | LOW post-fix | MEDIUM (1-3hr) | **YES** | FastAPI runtime route handler logic touched (exports.py:514,546); per dispatch criterion "F2 fix touches FastAPI route handler logic (likely YES — this IS source-code change)"; AUDIT §6 Flag #3 calls out missing test backstop. Specific Gate A questions: (i) is `_format_dataframe_response` JSON branch already envelope-wrapping? (ii) if not, do we proceed with handler change OR revert openapi.json (Sub-B regression)? |
| F3 | ACCEPT-WITH-FLAG | LOW (test-only threshold change) | HIGH (CI variance is inherent) | LOW (5min + ADR) | **YES** | ADR authoring is design decision; threshold-relax is calibration-against-CI-distribution which is platform-judgment; per dispatch criterion "F3 disposition is ACCEPT-WITH-FLAG (ADR authoring is design decision)" |

**Gate A summary**: 2 of 3 failures trigger Gate A. F1 proceeds without attestation; F2 + F3 require user attestation before janitor execution.

## §5 Verification Protocol (Post-Execution, audit-lead consumption)

Per failure, audit-lead verifies:

**F1 (Lint)**:
- Run on CI: `ci / Lint & Type Check` job, step `Run linting` = SUCCESS on the post-fix HEAD.
- Local re-verify: `uv run --no-sources ruff check .` exits 0.
- Test suite: `pytest tests/unit/api/` passes (the 4 affected test files specifically).

**F2 (OpenAPI drift)**:
- Run on CI: `ci / OpenAPI Spec Drift` = SUCCESS AND `ci / Spectral Fleet Validation` = SUCCESS on post-fix HEAD.
- Local re-verify: `uv run python scripts/generate_openapi.py --check` exits 0.
- Contract test present at `tests/unit/api/test_exports_envelope_contract.py` and passing (asserts `httpx.post('/v1/exports', …)` JSON response top-level keys = `{'data', 'meta'}`).
- File:line confirmation: `exports.py:514,546` no longer contain `response_model=None` (or, if Sub-B path taken, openapi.json:3736,8356 reverted to `schema: {}`).

**F3 (Perf flake)**:
- Run on CI: `ci / Test (shard 1/4)` SUCCESS on 5 consecutive runs post-fix.
- Local re-verify: `pytest tests/validation/persistence/test_performance.py::TestEndToEndPerformance::test_session_track_100_entities` passes 5x consecutively.
- ADR present at `.ledge/decisions/ADR-NNN-relax-persistence-perf-threshold.md` with file:line citation to the relaxed threshold + observed-variance evidence.
- Defer-watch entry present in `.know/defer-watch.yaml` with id `persistence-perf-wall-clock-flake-2026-04-29` and `escalation_target: /sre or /10x-dev rite Potnia`.

## §6 Authority Boundary and Handoff Criteria

Per architect-enforcer authority (per agent prompt):
- **MAY**: classify dispositions, sketch ADR content, identify defer-watch shapes (this PLAN does all three).
- **MAY NOT**: execute (janitor Phase 3); modify code; merge.

**Ready for janitor when**:
- [x] Every failure classified (F1: FIX, F2: FIX Sub-A, F3: ACCEPT-WITH-FLAG)
- [x] Each disposition has before/after contract (per §2.X options)
- [x] Verification criteria specified (per §5)
- [x] Atomic commit sequence with rollback points (per §3)
- [x] Risk assessment complete (per §4)
- [x] Gate A triggers identified (F2 + F3) — user attestation required before janitor execution

**Ready for user (Gate A) when**:
- [x] PLAN authored and inspected (this artifact)
- [ ] User reviews F2 Sub-A vs Sub-B trade-off (envelope-handler-shape investigation may shift recommendation)
- [ ] User reviews F3 ADR threshold rationale (1500ms ceiling — defensible? or relax further?)

## §7 Receipt-Grammar Attestation

Per F-HYG-CF-A discipline:
- F1 evidence: SMELL §F1 L33-L52 (failure signature + 9-file list); workflow-run `25109444280/job/73579200300`.
- F2 evidence: SMELL §F2 L66-L96; workflow-run `25109444280/job/73579200333`; SVR file-read receipts on `exports.py:514,546` (verified by direct read at audit time, output captured at §2.2 root-cause-confirmation block); openapi.json:3733-3741 + 8353-8361 verified via `sed` probe at audit time.
- F3 evidence: SMELL §F3 L100-L141; workflow-run `25109444280/job/73579221418`; test body verified verbatim at SMELL L125-136.
- Cross-rite handoff substrate: AUDIT-actual-blockers-2026-04-29.md §6 Flag #2 names these failures as out-of-scope for prior engagement and surfaces them for follow-up.

[UV-P: F2 Sub-A's branch-decision (response_model=SuccessResponse[…] vs runtime-handler envelope-wrap) depends on inspecting `_format_dataframe_response` JSON-branch behavior at `src/autom8_asana/api/routes/dataframes.py` | METHOD: deferred-to-janitor-execution | REASON: investigation requires reading the handler body which is janitor-Phase-3 work; architect-enforcer Phase-2 recommends Sub-A direction without committing to which branch (declaration-only vs handler-change) — Gate A presents both branches for user attestation]

---

*Authored by architect-enforcer 2026-04-29 under hygiene rite Phase 2 (planning) for "Follow-on CI Failure Triage". MODERATE evidence-grade per `self-ref-evidence-grade-rule`. Authority boundary: plan-and-recommend only; janitor executes Phase 3 under Gate A attestation for F2+F3. Receipt-grammar (F-HYG-CF-A) preserved: every claim file:line OR workflow-run URL OR explicit DEFER tag.*
