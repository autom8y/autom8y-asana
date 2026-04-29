---
artifact_id: PLAN-actual-blockers-2026-04-29
schema_version: "1.0"
type: spec
artifact_type: refactoring-plan
slug: actual-blockers-2026-04-29
rite: hygiene
phase: 2-planning
initiative: "Principled Actual-Blocker Remediation"
date: 2026-04-29
status: accepted
created_by: architect-enforcer
evidence_grade: MODERATE
self_grade_ceiling_rationale: "self-ref-evidence-grade-rule — architect-enforcer authoring within hygiene rite caps at MODERATE; STRONG would require external rite re-audit"
upstream_smell_report: .ledge/reviews/SMELL-actual-blockers-2026-04-29.md
upstream_handoff: .ledge/handoffs/HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md
verdict_substrate: .ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md
case_substrate: .ledge/reviews/CASE-comprehensive-cleanliness-2026-04-29.md
scar_substrate: .know/scar-tissue.md (SCAR-P6-001)
disciplines_applied:
  - option-enumeration-discipline
  - structural-verification-receipt
  - authoritative-source-integrity
  - defer-watch-manifest
  - satellite-primitive-promotion
items_in_scope:
  - HYG-001 (3 gates: Lint, Semantic Score, Spectral)
  - HYG-002 (drift-audit-discipline skill MINT)
items_out_of_scope:
  - OOS-1 (Node.js 20 deprecation — fleet altitude)
  - OOS-2 (4 Spectral warnings — non-blocking)
gate_a_attestation_required: true
gate_a_trigger_reason: "HYG-001 Gate B disposition crosses repo boundary (cross-package: changes to docs/api-reference/openapi.json materially mutate published API surface)"
authority_boundary:
  may_plan: true
  may_recommend_disposition: true
  may_sketch_adr: true
  may_execute: false
  may_author_canonical_clause_text: false
---

# PLAN — Actual-Blocker Refactoring Plan (2026-04-29)

## §1 Scope

**In-scope (2 items)** — drawn from `HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md:19-84`:

- **HYG-001** — Triage 3 stale CI gates (Lint & Type Check / Semantic Score Gate / Spectral Fleet Validation). Per-gate disposition required; no "TBD" at task close (handoff L29).
- **HYG-002** — drift-audit-discipline skill **MINT** (NOT-PROMOTE) per SMELL §2.1 (`SMELL-actual-blockers-2026-04-29.md:154-172`).

**Out-of-scope — surface to user via Potnia, do NOT absorb** (per handoff L156 "no scope creep"):

- **OOS-1** — Node.js 20 deprecation warnings on all 3 jobs (`SMELL §4.1` at `SMELL-actual-blockers-2026-04-29.md:252-260`). Fleet-altitude tooling-skew. Route candidate: `/sre` or fleet-tooling refresh.
- **OOS-2** — 4 Spectral warnings co-located with the 2 errors (`SMELL §4.2` at `SMELL-actual-blockers-2026-04-29.md:262-273`). Non-blocking under `--fail-severity=error` at `satellite-ci-reusable.yml@c88caabd:869`. Route candidate: future hygiene engagement at openapi.json altitude.

---

## §2 HYG-001 — Per-Gate Disposition (option-enumeration-discipline)

For each gate: enumerate FIX-TO-GREEN | DELETE-AS-OBSOLETE | ACCEPT-WITH-EXPLICIT-FLAG, then recommend.

### §2.1 Gate A — Lint & Type Check

Evidence anchor: `SMELL §1.1` at `SMELL-actual-blockers-2026-04-29.md:40-68`. Failure mechanism: `ruff format --check` exit code 1 against 7 specific files; workflow run `https://github.com/autom8y/autom8y-asana/actions/runs/25107487624/job/73572352438`. Code-fixable / invariant-violation classification per SMELL §1.1 L64.

**Option FIX-TO-GREEN**:
- Steps: Run `uv run ruff format` against the 7 files listed in `SMELL-actual-blockers-2026-04-29.md:54-60` (`src/autom8_asana/api/routes/_exports_helpers.py`, `src/autom8_asana/api/routes/exports.py`, `src/autom8_asana/models/business/detection/facade.py`, `tests/unit/api/test_exports_format_negotiation.py`, `tests/unit/api/test_exports_handler.py`, `tests/unit/api/test_exports_helpers_walk_predicate_property.py`, `tests/unit/services/test_discovery.py`). Stage and commit.
- Effort: <30 minutes.
- Risk: **LOW**. Behavior-preserving formatting only (whitespace / trailing comma / line-break normalization per ruff format rules); no semantic change. MUST-preserve list (public APIs, return types, error semantics) is not touched by formatter.
- Test verification: (a) `uv run ruff format . --check` returns exit 0 locally pre-commit; (b) push branch + open PR; (c) `ci / Lint & Type Check` job transitions FAILURE → SUCCESS on the new run.

**Option DELETE-AS-OBSOLETE**:
- Workflow change: remove `lint-typecheck` job invocation from `autom8y-asana/.github/workflows/test.yml` reusable-call (the job is defined upstream at `satellite-ci-reusable.yml@c88caabd:221-366`; the satellite repo can disable it via reusable input or by switching to a non-linting reusable variant). No file in this repo currently disables it.
- Justification: would require asserting "the fleet does not need `ruff format` enforcement at PR time" — there is no such assertion on the table.
- Coverage gap: 1057 files (1050 already formatted + 7 newly formatted post-fix) lose pre-merge format enforcement; format drift would re-accumulate.
- Mitigation: pre-commit hook would partially mitigate, but no fleet-wide pre-commit hook exists in autom8y-asana per inspection of `.pre-commit-config.yaml` (file absent).

**Option ACCEPT-WITH-EXPLICIT-FLAG**:
- ADR location: `.ledge/decisions/ADR-NNNN-accept-lint-failure.md`. Content sketch: would need to assert "ruff format violations on 7 specific files are structurally non-fixable." There is no such structural argument — the files are mutable, the formatter is deterministic, the fix is a single command. **ACCEPT is not on the table** (the gate is not structurally non-fixable; it is trivially fixable).
- Defer-watch entry: would be ill-formed (no watch_trigger; no escalation owner; no deadline that maps to anything).
- CI configuration: would set `continue-on-error: true` on `lint-typecheck`, but this defeats the gate's signal entirely with no offsetting structural justification.

**Recommended disposition: FIX-TO-GREEN**. Rationale: code-fixable invariant-violation per SMELL §1.1 L64 (cheap; restores signal; no structural blocker); DELETE creates a coverage gap with no compensating mechanism; ACCEPT has no structural argument to anchor.

---

### §2.2 Gate B — Semantic Score Gate

Evidence anchor: `SMELL §1.2` at `SMELL-actual-blockers-2026-04-29.md:72-107`. Two co-occurring failure signals: M-05 type strictness regression `delta: -0.0046` and M-07 constraint coverage floor violation. Workflow run `https://github.com/autom8y/autom8y-asana/actions/runs/25107487624/job/73572352423`. Stale-baseline + invariant-violation per SMELL §1.2 L98.

**Option FIX-TO-GREEN (decomposed; both sub-options are fix variants)**:
- **Sub-option B1 — Baseline-refresh** (covers the stale-baseline component): regenerate the canonical baseline at `inputs.semantic_score_baseline` (configured at `test.yml:64` per SMELL §1.2 reading) IF current `docs/api-reference/openapi.json` reflects current API intent. Steps: re-run `score_spec.py` against current openapi.json; commit refreshed baseline JSON. Effort: <1 hour. Risk: **MEDIUM** — refreshing the baseline accepts the M-05 regression as the new floor; this is an architecturally-load-bearing choice (the regression-gate intent is to BLOCK quality drift, not auto-accept it).
- **Sub-option B2 — Code-fix the openapi.json** (covers the invariant-violation component): tighten field types in `docs/api-reference/openapi.json` to raise M-05 strictness back above prior baseline AND add constraints (formats / patterns / enums) to push M-07 above floor. Effort: ~1 day (requires inspection of which fields regressed and which lack constraints). Risk: **MEDIUM-HIGH** — schema mutations propagate to all consumers of the published API surface; cross-package impact (this is the Gate A trigger; see §6).
- **Sub-option B3 — Hybrid**: refresh baseline for the M-07 floor (if floor was set aspirationally) AND code-fix the M-05 regression (preserving regression-gate signal). Effort: ~half day. Risk: **MEDIUM**.
- Test verification (all sub-options): `ci / Semantic Score Gate` transitions FAILURE → SUCCESS on a fresh PR; score-result.json `regression_safe: true` and `floor_violations: []`.

**Option DELETE-AS-OBSOLETE**:
- Workflow change: remove `semantic-score` reusable input from `test.yml` OR set `inputs.run_semantic_score: false` (verify input exists at `satellite-ci-reusable.yml@c88caabd:932-1010`).
- Justification: would require the assertion "the fleet no longer values type strictness / constraint coverage on its OpenAPI surface." The Spectral gate (Gate C) catches a *different* class of issue (envelope conformance) — it does NOT subsume the Semantic Score gate's strictness/coverage signals.
- Coverage gap: type-strictness regressions and constraint-coverage drift become invisible at PR time across the fleet. This is the gate's entire telos.
- Mitigation: none currently in the satellite stack.

**Option ACCEPT-WITH-EXPLICIT-FLAG**:
- ADR sketch (`.ledge/decisions/ADR-NNNN-accept-semantic-score-regression.md`): assert "the M-05 -0.0046 regression and M-07 floor violation are accepted because [structural reason]." Candidate structural reasons: (a) baseline reflects an intent that is being deliberately deprecated; (b) M-07 constraint coverage requires breaking-change schema work scheduled at a different altitude. Neither structural reason is established at this engagement; ADR authoring would itself require a sprint of investigation.
- Defer-watch entry shape (per `defer-watch-manifest` skill): `id: DEFER-HYG001-GATE-B`, `watch_trigger: openapi.json materially mutated OR baseline regenerated`, `deadline: 2026-07-29` (90d from today, aligning with WS4-T3 conventions per `.know/scar-tissue.md` cross-reference at the inaugural-hygiene-cleanup entry), `escalation_owner: hygiene rite Potnia`.
- CI configuration: `continue-on-error: true` on `semantic-score` job + commented annotation citing the ADR.

**Recommended disposition: FIX-TO-GREEN via Sub-option B3 (hybrid)**. Rationale: the SMELL classification is mixed (stale-baseline + invariant-violation) — neither pure baseline-refresh (B1) nor pure code-fix (B2) cleanly addresses both signals. B3 preserves the regression-gate's structural intent while clearing the floor violation. **CAVEAT**: if openapi.json mutation in B2/B3 mutates published API surface (e.g., tightening a field type from `string` to `string + pattern`), this is a **contract change**, not a refactor — escalates to user per Behavior Preservation MUST-list (see §6 Gate A). DELETE has no compensating mechanism; ACCEPT lacks a structural argument today.

---

### §2.3 Gate C — Spectral Fleet Validation

Evidence anchor: `SMELL §1.3` at `SMELL-actual-blockers-2026-04-29.md:111-135`. Failure mechanism: 2 `fleet-envelope-consistency` errors at `docs/api-reference/openapi.json:3736:26` and `:8356:26` — the 200-response schemas for `/api/v1/exports.post` and `/v1/exports.post` do not follow the fleet `{data, meta}` envelope. Workflow run `https://github.com/autom8y/autom8y-asana/actions/runs/25107487624/job/73572352495`. Code-fixable / invariant-violation per SMELL §1.3 L131.

**Option FIX-TO-GREEN**:
- Steps: edit `docs/api-reference/openapi.json` at line 3736 (path `/api/v1/exports.post` 200 response) and line 8356 (path `/v1/exports.post` 200 response) to wrap the response schemas in the canonical `{data: {...}, meta: {...}}` envelope structure required by the fleet rule. The exact target shape is defined in the cross-repo fleet ruleset at `autom8y/autom8y-api-schemas` repo (`spectral-fleet.yaml` — fetched at `satellite-ci-reusable.yml@c88caabd:847-859`); architect-enforcer notes the exact schema shape is the janitor's read-target, not pre-decided here.
- Effort: ~1-2 hours per endpoint (4h total) — schema authoring + downstream consumer-impact check.
- Risk: **MEDIUM-HIGH** — wrapping the 200 response in `{data, meta}` is a **breaking change** for consumers that read the prior un-enveloped shape directly. This is materially a contract change. Cross-package impact (Gate A trigger; see §6).
- Test verification: (a) local `npx @stoplight/spectral-cli lint docs/api-reference/openapi.json --ruleset .fleet-schemas/spectral-fleet.yaml --fail-severity=error` returns 0 errors; (b) push branch + PR; (c) `ci / Spectral Fleet Validation` transitions FAILURE → SUCCESS.

**Option DELETE-AS-OBSOLETE**:
- Workflow change: remove `spectral-validation` job invocation from `test.yml` OR set the relevant reusable input to false.
- Justification: would require the assertion "the fleet no longer enforces envelope consistency on satellite OpenAPI specs." This rule is part of the cross-repo `autom8y-api-schemas` canonical ruleset — disabling at one satellite implies fleet-wide deviation.
- Coverage gap: envelope-shape drift across fleet satellites; this is the rule's entire purpose (cross-satellite uniformity).
- Mitigation: none.

**Option ACCEPT-WITH-EXPLICIT-FLAG**:
- ADR sketch (`.ledge/decisions/ADR-NNNN-accept-spectral-envelope-deviation.md`): assert "the `/exports.post` 200 responses are accepted as un-enveloped because [structural reason]." Candidate structural reasons: (a) the exports endpoint streams a CSV/file payload where the envelope wrapper is semantically wrong; (b) the endpoint predates the envelope rule and rewrap is a coordinated breaking-change scheduled separately. (a) is plausible and warrants user adjudication; (b) is plausible and warrants scheduling.
- Defer-watch entry: `id: DEFER-HYG001-GATE-C`, `watch_trigger: exports.post response shape materially mutated OR fleet rule revised`, `deadline: 2026-07-29`, `escalation_owner: hygiene rite Potnia`.
- CI configuration: `continue-on-error: true` on `spectral-validation` job + ADR citation comment.

**Recommended disposition: FIX-TO-GREEN with user attestation OR ACCEPT-WITH-EXPLICIT-FLAG (ADR + defer-watch) — choice escalates to user**. Rationale: both errors are technically code-fixable (SMELL §1.3 fixability signal), but the fix is a contract-altering schema change that crosses the Behavior Preservation MUST-list ("public API signatures", "return types", "documented contracts" — Architect-Enforcer agent prompt § Behavior Preservation). Architect-enforcer does NOT decide between FIX (with user attestation) vs ACCEPT (with ADR) for contract-altering changes — escalates per agent-prompt § "You Escalate" → "Refactoring that would change public API contracts → escalate to user." See §6 Gate A.

---

## §3 HYG-002 — drift-audit-discipline Skill MINT (option-enumeration-discipline)

Evidence anchor: `SMELL §2.1` at `SMELL-actual-blockers-2026-04-29.md:154-172`. **MINT-NOT-PROMOTE** condition (skill body absent at all searched altitudes per SMELL §2.1 search trace L160-L170).

### §3.1 Three options enumerated

**Option A — Repo-local mint** at `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.claude/skills/drift-audit-discipline/SKILL.md`:
- Pros: immediately available to this repo's hygiene/eunomia/review agents; no satellite-primitive-promotion protocol invocation; aligns with hygiene-rite authority boundary (handoff L119: "Modify knossos skill files" is granted, but knossos altitude is outside this repo).
- Cons: not fleet-wide — other satellites (autom8y-cli, autom8y-platform, etc.) won't inherit; risks divergence at promotion time if satellite-specific divergence accrues before promotion.
- Effort: ~half day (skill body authoring + cross-link to SCAR-P6-001).
- Risk: **LOW**.

**Option B — Knossos-altitude mint** at `/Users/tomtenuta/Code/knossos/rites/shared/mena/drift-audit-discipline/SKILL.md`:
- Pros: fleet-wide canonical altitude; immediately available to all rites that inherit shared-mena.
- Cons: requires `satellite-primitive-promotion` protocol invocation (skill at `.claude/skills/satellite-primitive-promotion/`); requires user-attestation gate per the protocol's branching/sync ordering; cross-repo coordination with knossos repo; longer time-to-availability.
- Effort: ~1 day per handoff L84 estimate.
- Risk: **MEDIUM** — knossos altitude is outside the autom8y-asana session repo; the handoff at L80-L82 explicitly requires escalation back to hygiene-rite Potnia for routing.

**Option C — Repo-local mint NOW + satellite-primitive-promotion follow-up** (hybrid):
- Pros: immediately available (closes the recurrence-prevention gap NOW per SMELL §2.2 "Implications" L177); explicit promotion path scheduled via defer-watch; matches hygiene-rite authority boundary (repo-local) without precluding fleet-wide.
- Cons: two-stage authoring; near-term divergence risk during the promotion window (mitigated by short defer-watch deadline).
- Effort: ~half day (Stage 1) + later promotion sprint (Stage 2).
- Risk: **LOW** for Stage 1; deferred to promotion sprint for Stage 2.

### §3.2 Synthesis-altitude clause text — TWO CANDIDATE FORMS to reconcile

Per SMELL §2.3 L192-L198, the originating evidence chain carries two forms of the clause; reconciliation is architect-enforcer's authority. **The architect-enforcer SKETCHES the reconciled form below for janitor authoring; the canonical clause text is authored by janitor at Phase-3 commit time per authority-boundary § "MAY NOT author canonical clause text as final canonical text."**

- **Form-1 (compact)** — VERDICT §5 recommendation 2 at `VERDICT-eunomia-final-adjudication-2026-04-29.md:135-137` and SCAR-P6-001 at `.know/scar-tissue.md:230-231`:
  > *"Re-run drift-audit at any altitude where mixed-resolution upstream substrates are being consolidated."*
- **Form-2 (expanded)** — handoff at `HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md:56`:
  > *"re-run drift-audit at any altitude where mixed-resolution upstream substrates are being consolidated. Specifically: any plan-authoring step that consumes [UNATTESTED] inventory framing MUST verify ground truth against origin/main before propagating the framing forward."*

**Architect-enforcer reconciliation sketch** (NOT canonical — janitor authors final canonical text in Phase 3):
- Form-2 is Form-1 + a specific application clause naming `[UNATTESTED]` inventory framing and origin/main verification. Form-2 is strictly more specific; it does not contradict Form-1; it operationalizes it.
- **Sketched reconciled shape**: skill body carries Form-1 as the throughline / general rule and Form-2 as the operational sub-clause under the §2 HOW or §1 WHEN section per SMELL §2.5 siting candidates (`SMELL-actual-blockers-2026-04-29.md:226-230`).

### §3.3 Recommended disposition: **Option C (hybrid)**

Rationale: closes the recurrence-prevention gap immediately at the altitude where the recurrence already happened (this satellite repo at PLAN-authoring altitude per VERDICT §5); preserves explicit fleet-wide promotion path via defer-watch; aligns with hygiene-rite authority boundary (handoff L126-L129 — repo-local skill modification is granted; cross-repo modification routes via satellite-primitive-promotion). Stage-2 promotion is filed as a defer-watch entry (`id: DEFER-HYG002-FLEET-PROMOTION`, `watch_trigger: a second satellite repo encounters Pattern-6-recurrence absent the discipline OR fleet retro identifies cross-satellite need`, `deadline: 2026-07-29`, `escalation_owner: hygiene rite Potnia`).

---

## §4 Atomic Commit Plan

Per HYG-NNN, sequenced low-to-high risk; one commit per disposition target (the audit-lead can revert atomically).

### §4.1 HYG-001 commit decomposition

| # | Commit subject | Files modified | Risk | Depends-on |
|---|---|---|---|---|
| C1 | `style(api,tests): apply ruff format to 7 unformatted files` | 7 files per §2.1 | LOW | — |
| C2 (conditional on user attestation; see §6) | `fix(openapi): tighten M-05 strictness; add M-07 constraints; refresh semantic-score baseline` | `docs/api-reference/openapi.json` + baseline JSON path per `test.yml:64` config | MEDIUM | — (independent of C1 logically; sequence C1 first to land low-risk fix early) |
| C3 (conditional on user attestation OR ACCEPT path; see §6) | If FIX path: `fix(openapi): wrap exports.post 200 responses in fleet {data,meta} envelope`. If ACCEPT path: `chore(ci): accept Spectral envelope deviation on exports.post per ADR-NNNN` | If FIX: `docs/api-reference/openapi.json` at L3736 + L8356. If ACCEPT: `.github/workflows/test.yml` (continue-on-error annotation) + `.ledge/decisions/ADR-NNNN-accept-spectral-envelope-deviation.md` + `.know/defer-watch.yaml` entry | MEDIUM-HIGH (FIX) / LOW (ACCEPT) | — |

**HYG-001 PR strategy** per handoff L157 ("HYG-001 may decompose to 3 PRs if 3 separate disposition strategies emerge"): one PR per commit-pair, OR one consolidated PR with the 3 atomic commits — janitor decides at execution time per `conventions` skill. Atomic-commit discipline preserves per-commit `git revert` safety.

### §4.2 HYG-002 commit decomposition

| # | Commit subject | Files modified | Risk | Depends-on |
|---|---|---|---|---|
| C4 | `feat(skills): mint drift-audit-discipline skill (Option C Stage 1) with synthesis-altitude clause; cross-link SCAR-P6-001` | `autom8y-asana/.claude/skills/drift-audit-discipline/SKILL.md` (NEW); `.know/scar-tissue.md` (cross-link addition at SCAR-P6-001 §Defensive discipline); `.know/defer-watch.yaml` (DEFER-HYG002-FLEET-PROMOTION entry) | LOW | — |

**HYG-002 PR strategy**: separate PR from HYG-001 per handoff L157 ("Atomic commits/PRs per item") and per HANDOFF L123 ("separate PRs per HYG-NNN preferred for atomic revertability").

### §4.3 Sequencing (low-to-high risk)

**Phase 2a (LOW risk, no user attestation)**: C1 (Lint format fix), C4 (skill mint).
**Phase 2b (MEDIUM/HIGH risk, gated on user attestation)**: C2 (Semantic Score), C3 (Spectral).

**Rollback points**:
- After Phase 2a: stable green-or-near-green CI on Lint + skill body materialized; revert via `git revert C1` and/or `git revert C4` if regression.
- After Phase 2b each commit: per-commit `git revert` safety. C2 and C3 are independent (touch different sections of openapi.json + different ADR/baseline paths).

---

## §5 Risk Classification + Sequence

### §5.1 Risk matrix

| Commit | Blast radius | Likelihood of regression | Rollback cost | Composite risk |
|---|---|---|---|---|
| C1 (Lint) | 7 files, formatter-only | Very low (deterministic formatter) | Trivial (`git revert`) | **LOW** |
| C2 (Semantic Score) | openapi.json published surface + baseline | Medium (schema mutations propagate) | Low-Medium (revert restores prior baseline + schema) | **MEDIUM** |
| C3 FIX path (Spectral) | openapi.json public response shape | High (breaking change for un-enveloped consumers) | Medium (revert un-breaks consumers but restores red gate) | **MEDIUM-HIGH** |
| C3 ACCEPT path (Spectral) | CI annotation only | Very low | Trivial | **LOW** |
| C4 (skill mint) | New skill file + 2 cross-link edits | Very low (additive only) | Trivial (`git revert`) | **LOW** |

### §5.2 Recommended execution order

1. **C1** (Lint format) — first; LOW risk; clears one gate signal immediately.
2. **C4** (skill mint) — independent of HYG-001; can run in parallel or interleaved; LOW risk; closes recurrence-prevention gap immediately.
3. **GATE A (user attestation; see §6)** — halt before C2 and C3 if FIX paths.
4. **C2** (Semantic Score B3 hybrid) — after Gate A; isolates Semantic Score signal mutation.
5. **C3** (Spectral) — last; highest blast radius if FIX; OR LOW if ACCEPT.

### §5.3 Halt-on-failure discipline

Per `conventions` skill + handoff acceptance L160 ("Audit-lead sign-off post-execution"): if any commit fails its verification (per §7), HALT subsequent commits in the sequence; do NOT cascade. Escalate failure mode to architect-enforcer for re-planning. Per agent-prompt § "Risk sequencing errors": no high-risk commit precedes its low-risk antecedent without justification — C1 + C4 land first by design.

---

## §6 User Attestation Gate (Gate A)

Per handoff acceptance criterion L158: *"User attestation gate before HYG-001 disposition execution if any of the 3 gates resolves to FIX-TO-GREEN with non-trivial code changes."*

**Gate A FIRES.** Triggering conditions:

1. **HYG-001 Gate B (Semantic Score) recommended FIX-TO-GREEN via Sub-option B3** mutates `docs/api-reference/openapi.json` (cross-package — published API surface); LoC delta is openapi.json schema-shape-dependent but materially exceeds the >20 LoC threshold OR crosses the cross-package threshold per handoff L130 framing.
2. **HYG-001 Gate C (Spectral) FIX path** wraps `/api/v1/exports.post` and `/v1/exports.post` 200 responses in `{data, meta}` envelope — this is a **public API contract change** per Architect-Enforcer agent prompt § Behavior Preservation MUST-list ("public API signatures", "return types", "documented contracts"). Independent of LoC count, contract-altering refactors require user attestation.

**User attestation surface (what the user adjudicates)**:

| Question | Owner | Default if user defers |
|---|---|---|
| Q-A1: Approve C2 (Semantic Score B3 hybrid) — refresh M-07 floor + code-fix M-05 regression in openapi.json? | User | HALT; consider B1 baseline-only OR ACCEPT-with-flag re-route |
| Q-A2: For C3 (Spectral), select FIX vs ACCEPT? FIX is a breaking change to `exports.post` 200 response shape; ACCEPT requires ADR + defer-watch. | User | HALT; default to ACCEPT path (lower-risk rollback) pending user decision |

**Pre-Gate-A commits permitted without attestation**: C1 (Lint format) and C4 (skill mint) — both are LOW risk, neither crosses MUST-preserve list, neither exceeds LoC/cross-package thresholds.

---

## §7 Verification Protocol (post-execution)

Audit-lead verification per item:

| Commit | Verification method | Pass criterion |
|---|---|---|
| C1 (Lint) | `gh pr checks <PR#>` after push | `ci / Lint & Type Check` state SUCCESS; SVR receipt grammar: file:line evidence at all 7 files reformatted (verifiable by `git diff --stat HEAD~1`) |
| C2 (Semantic Score) | `gh pr checks <PR#>` + score-result.json inspection | `ci / Semantic Score Gate` state SUCCESS; `regression_safe: true`; `floor_violations: []`; SVR receipt grammar: workflow-run URL captured in audit artifact |
| C3 FIX (Spectral) | `gh pr checks <PR#>` + local spectral lint | `ci / Spectral Fleet Validation` state SUCCESS; spectral lint exit code 0; SVR receipt grammar: workflow-run URL + openapi.json:3736 + :8356 verified shape |
| C3 ACCEPT (Spectral) | ADR file present + defer-watch entry present + workflow annotation present | ADR file exists at `.ledge/decisions/ADR-NNNN-accept-spectral-envelope-deviation.md`; `.know/defer-watch.yaml` contains `DEFER-HYG001-GATE-C` entry; `test.yml` carries `continue-on-error: true` on spectral-validation job with comment-anchor citing ADR |
| C4 (skill mint) | File-system verification + grep verification | `find /Users/tomtenuta/Code/a8/repos/autom8y-asana/.claude/skills -type d -name "drift-audit-discipline"` returns the path; `grep -l "drift-audit-discipline" .know/scar-tissue.md` returns SCAR-P6-001 cross-link; `grep -l "DEFER-HYG002-FLEET-PROMOTION" .know/defer-watch.yaml` returns hit |

**Audit-lead sign-off (per handoff L160)**: all 5 commits verified per the table above; `gh pr checks` JSON output captured in audit artifact; SVR receipts (file:line + workflow-run URL) preserved in audit-lead's deliverable.

---

## §8 Authority Boundary Compliance

| Boundary | Compliance | Anchor |
|---|---|---|
| MAY plan, recommend dispositions, sketch ADR content, identify defer-watch shapes | Compliant — §2 enumerates 3 options per gate; §3 enumerates 3 options for skill mint; §6 sketches Gate A questions; defer-watch shapes specified at §2.2 + §2.3 + §3.3 | Architect-Enforcer agent prompt § "You Decide" |
| MAY NOT execute (janitor's Phase 3) | Compliant — no file modifications outside this deliverable | task spec authority boundary |
| MAY NOT modify code | Compliant — read-only across SMELL/HANDOFF/VERDICT/CASE/SCAR; only this deliverable file written | task spec |
| MAY NOT author canonical synthesis-altitude clause text | Compliant — §3.2 reconciles two extant forms as a SKETCH; canonical authoring routed to janitor in Phase 3 | task spec ("planning sketches it; executor authors it during Phase 3 commit") |
| Receipt-grammar (F-HYG-CF-A): every claim file:line OR workflow-run URL OR explicit DEFER tag | Compliant — every per-gate disposition cites SMELL §1.N file:line + workflow-run URL; HYG-002 cites SMELL §2.N file:line; option-enumeration cites file:line per option | F-HYG-CF-A canonical at `RETROSPECTIVE-VD3-2026-04-18.md:145` |
| Self-grading ceiling MODERATE | Compliant — frontmatter `evidence_grade: MODERATE`; `self_grade_ceiling_rationale` cites self-ref-evidence-grade-rule | task spec self-grading ceiling |

---

## §9 Source Manifest

| Role | Artifact | Absolute path |
|---|---|---|
| Phase-1 deliverable (primary upstream) | SMELL-actual-blockers | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/SMELL-actual-blockers-2026-04-29.md` |
| Originating handoff | cleanup → hygiene HANDOFF | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/handoffs/HANDOFF-cleanup-to-hygiene-actual-blockers-2026-04-29.md` |
| Cite-only authority | eunomia VERDICT | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md` |
| Cite-only authority | review CASE | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/CASE-comprehensive-cleanliness-2026-04-29.md` |
| Cite-only scar | SCAR-P6-001 | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/scar-tissue.md` (entry at L201-L238) |
| Defer-watch registry target | defer-watch.yaml | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.know/defer-watch.yaml` |
| THIS artifact | PLAN-actual-blockers | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/specs/PLAN-actual-blockers-2026-04-29.md` |

---

*Authored by architect-enforcer 2026-04-29 under hygiene rite Phase 2 (planning) for the "Principled Actual-Blocker Remediation" initiative. MODERATE evidence-grade per `self-ref-evidence-grade-rule`. Option-enumeration-discipline applied per gate (HYG-001 §2.1/§2.2/§2.3) and per skill-mint condition (HYG-002 §3). Authority boundaries observed: dispositions recommended (not executed); ADR content sketched (not authored); defer-watch shapes identified (not committed); canonical synthesis-altitude clause text reconciled as a sketch (not authored). Gate A user attestation FIRES on HYG-001 Gate B (Semantic Score B3 hybrid) and Gate C (Spectral FIX vs ACCEPT). Phase-3 handoff to janitor ready.*
