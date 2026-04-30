---
artifact_id: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3
schema_version: "1.0"
type: design
artifact_type: charter
slug: sprint3-2026-04-30
rite: sre
initiative: sre-sprint3-path-b-and-sre-005-discharge
complexity: INITIATIVE
phase_posture: PLAN
session_id: session-20260430-203219-c8665239
parent_session: session-20260430-115401-513947b2
parent_charter: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2
authored_by: pythia (consultative throughline) + main-thread (materialization)
authored_at: 2026-04-30
evidence_grade: MODERATE
self_grade_ceiling_rationale: "Pythia self-authoring; MODERATE per self-ref-evidence-grade-rule"
authoring_style: prescriptive-charter
governance_status: governing
authority_shift: "user authority grant 2026-04-30T18:31Z LIFTS Sprint-2 §7.1 cross-repo gate"
inherits_from:
  - PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2 (parent /sre Sprint-2 charter)
  - PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf (great-grandparent perf charter)
  - ADR-008/009/010 (Sprint-2 NO-LEVER ADRs framing Path B)
  - VERDICT-test-perf-2026-04-29-postmerge-supplement §9.6 (PASS-WITH-FLAGS-PRESERVED)
  - VERDICT-eunomia-final-adjudication-2026-04-29 §7 (M-16 source)
status: proposed
---

# PYTHIA INAUGURAL CONSULT — /sre Sprint-3 (sprint3-2026-04-30)

## §1 Telos Restatement

User invocation (verbatim, 2026-04-30T18:31Z):

> *"--to=sre for @potnia (agent) to orchestrate our /sprint to remediate:*
> *1) SRE-005 M-16 Dockerfile*
> *2) Path B cross-repo runner (you have full authority and access to the full file tree)"*

### §1.1 Authority Shift (LOAD-BEARING)

User's "full authority and access to the full file tree" clause **EXPLICITLY LIFTS** parent /sre Sprint-2 charter §7.1 cross-repo authorization gate. Cross-repo PRs against `autom8y/autom8y-workflows` are now in-scope. Multi-satellite SHA-pinning ramp protocol (parent §7.2) and chaos-engineer canary (parent §7.3) survive as **operational discipline**, not authorization gates.

This shift is the single most load-bearing reframe at engagement inception. Specialists MUST NOT re-litigate authorization downstream.

### §1.2 Engagement-chain context

Sprint-3 is the structural successor that closes the last non-multi-sprint residuals from the parent eunomia perf engagement:
- PR #44 (perf-track, -49% local pytest)
- PR #45 (HYG-001 SCAR codification)
- PR #46 (Sprint-2 NO-LEVER × 4 ADRs)
- PR #47 (hygiene Phase 1)
- PR #48 (hygiene Phase 2; HYG-004 fully discharged)
- **THIS Sprint-3** — Path B unlock + SRE-005

### §1.3 Anchor-return question

Three named user-visible outcomes verifiable by rite-disjoint measurement:
- (a) `autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml` parameterized + runner-tier upgraded; cross-repo PR landed
- (b) Hadolint integrated into pre-commit + CI Dockerfile lint enforcement
- (c) Post-merge CI shard p50 measured: ≥20% reduction → PASS-CLEAN-PROMOTION; <20% → PASS-WITH-FLAGS-PRESERVED

### §1.4 Telos-integrity gate (HARD prerequisite)

Charter authoring REQUIRES authorship of `.know/telos/sprint3-path-b-2026-04-30.md` per `telos-integrity-ref` schema. Sub-sprint C cannot close without this declaration in place. Required fields:
- inception_anchor.framed_at: 2026-04-30
- shipped_definition.user_visible_surface: CI shard p50 + Dockerfile lint enforcement
- verified_realized_definition.verification_method: telemetry + cross-stream-corroboration via eunomia VERDICT re-discharge
- verified_realized_definition.verification_deadline: Sprint-3 close + 14d
- rite_disjoint_attester: eunomia (continuing from Sprint-2 supplement)

## §2 Engagement Scope

| Field | Lock |
|---|---|
| Track | Cross-repo CI infrastructure (autom8y/autom8y-workflows) + Dockerfile pattern enforcement |
| Complexity | **INITIATIVE** (cross-repo + multi-satellite ramp + parallel sub-sprints) |
| Phase posture | **PLAN** (this charter precedes A1 + B1 dispatch) |
| Sprint structure | A (Path B) ∥ B (SRE-005) → C (close); A and B independent surfaces |
| Pantheon | platform-engineer (A1/A2/A4/B1/B2) \| chaos-engineer (A3) \| observability-engineer (C) \| incident-commander (STANDBY) \| potnia (orchestrator) |
| Authority | full in-rite + cross-repo via §1.1 shift; SHA-pin ramp + canary discipline survive |
| Inviolable constraints | drift-audit re-dispatch, SCAR ≥47, halt-on-fail, refusal posture (§8) |
| Branch | `sre/sprint3-path-b-2026-04-30` (cut from main@e3b5749e = PR #48 merge) |

## §3 Inheritance Audit (per `inherited-charter-audit-discipline`)

### §3.1 INHERITED (preserved verbatim)
- **Pattern-6 drift-audit re-dispatch** (parent Sprint-2 §3.1, great-grandparent perf §4.1)
- **SCAR cluster preservation** (≥47 markers operational since HYG-001)
- **Halt-on-fail discipline** (parent perf §8.3)
- **Refusal posture** (parent Sprint-2 §8.4)
- **Atomic-revertibility per commit** (parent perf §8.5)
- **Cross-repo SHA-pin ramp protocol** (parent Sprint-2 §7.2)
- **Chaos-engineer canary requirement** (parent Sprint-2 §7.3)
- **Verdict-discharge contract** (parent Sprint-2 §9; ≥20% threshold)

### §3.2 APPENDED (new at Sprint-3 altitude)
- **Authority-shift §1.1 LIFTS parent §7.1**: cross-repo PR authoring is now in-scope
- **Q1(a) BUNDLED PR**: runner-tier + worker-count parameterization in single cross-repo PR
- **Q2(a) HADOLINT with B1 confirmation gate**: tool selection contingent on B1 audit
- **Q3(b) SEPARATE PR for step-level optimizations**: blast-radius minimization preferred over bundling
- **Q4 cross-fleet ramp**: 8 consuming satellites enumerated; staging order + 3-criterion abort
- **Telos-integrity gate** (§1.4): `.know/telos/` declaration is HARD Sub-sprint C prerequisite

### §3.3 DELTA'd (none expected)
Charter EXTENDS parent Sprint-2; does not contradict.

## §4 Sub-sprint A Charter — Path B Cross-Repo (BLOCKING)

### §4.1 Q1 Adjudication: BUNDLED PR
Both runner-tier upgrade + worker-count parameterization in single cross-repo PR against `autom8y/autom8y-workflows`. Counter-options rejected on:
- (b) sequential: doubles ramp cycles + maintainer review surface
- (c) parameterization-first: defers measurable wallclock improvement

### §4.2 PR target surface
`autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml`:
- L393 (runner-tier): `runs-on: ubuntu-latest-large` (4-vCPU paid tier) — back-compat via input parameter `runner_size: 'standard' | 'large'`, default `'standard'`
- L527-528 (worker-count): `-n ${{ inputs.test_workers }}` with `default: 0` sentinel preserving `-n auto` legacy semantics

### §4.3 A1 — Per-step wallclock audit (platform-engineer)

6-step protocol:
1. Read `autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml` (full file via filesystem access per §1.1)
2. Capture 5 successful CI runs from autom8y-asana main branch via `gh run view --json jobs`
3. Extract per-step durations within each test shard job
4. Identify steps contributing to ~463s/shard CI fixed-overhead (per ADR-010 diagnosis)
5. Cross-reference against typical step taxonomy: checkout, setup-uv, install, mypy, spec-check, test execution, teardown
6. Author `.sos/wip/sre/AUDIT-path-b-cross-repo-2026-04-30.md` (~200 lines)

### §4.4 A2 — Cross-repo PR authoring (platform-engineer)

After A1 lands:
- Modify reusable workflow per §4.2 schema
- Add matrix self-test exercising both default paths (back-compat preservation)
- Author commit message inscribing authority chain (user authority → ADR-008/009 → this charter §1.1)
- Open PR against `autom8y/autom8y-workflows` with measured before/after wallclock evidence
- ADR-012 authored at `.ledge/decisions/ADR-012-path-b-runner-tier-and-worker-count-2026-04-30.md`

### §4.5 A3 — Chaos-engineer canary validation

Canary satellite: **autom8y-asana** (this repo). 3-run sample. **Abort criteria** (per Q4 adjudication):
- (a) **Green-rate delta**: any 0% < flake-rate ≤ 33% across canary 3-run → HALT
- (b) **p50 regression**: post-canary slowest-shard p50 > 469s (BASELINE 447s + 5%) → HALT
- (c) **Cycle-time degradation**: end-to-end PR-CI wallclock > pre-Path-B mean + 10% → HALT (catches `ubuntu-latest-large` queue-depth pathology)

### §4.6 A4 — Cross-fleet SHA-pin ramp

Q4 enumerates 8 consuming satellites of `autom8y/autom8y-workflows`. **Staging order** (lowest-to-highest blast-radius):
1. autom8y-asana (canary, A3 already validated)
2. autom8y-dev-x
3. autom8y-api-schemas
4. autom8y-data
5. autom8y-scheduling
6. autom8y-sms
7. autom8y-hermes
8. autom8y-ads

Per-satellite: pin to new SHA via `actions/checkout@<sha>` reference; observe 1 successful CI run per satellite; advance to next.

## §5 Sub-sprint B Charter — SRE-005 M-16 Dockerfile (parallel with A)

### §5.1 Q2 Adjudication: HADOLINT with B1 confirmation gate
Hadolint is the standard purpose-built tool. B1 audit MUST confirm:
- Maintenance status (last 12 months active)
- `hadolint-action@v3.x` SHA-pin compatibility
- Rule-corpus appropriate for autom8y-asana Dockerfile + Dockerfile.dev patterns

If B1 surfaces maintenance gap → escalate Q2 re-adjudication to user.

### §5.2 B1 — Dockerfile audit + tool select (platform-engineer)

5-step protocol:
1. `find . -name 'Dockerfile*' -not -path './.git/*' -not -path './.worktrees/*'` enumerate
2. Read each; classify by purpose (production, dev, test)
3. Verify hadolint covers M-16 patterns (per VERDICT-eunomia-final-adjudication §7)
4. Confirm hadolint maintenance status + version compatibility
5. Author `.sos/wip/sre/AUDIT-sre-005-dockerfile-2026-04-30.md` (~150 lines)
6. ADR-013 authored at `.ledge/decisions/ADR-013-sre-005-hadolint-2026-04-30.md`

### §5.3 B2 — Hadolint integration (platform-engineer)

After B1 lands:
- Add `.hadolint.yaml` config (M-16 pattern set codified)
- Add `hadolint/hadolint-action@<sha>` step to `.github/workflows/test.yml` (or new workflow file if separation-of-concerns warranted)
- Add pre-commit hook entry if pre-commit framework in use
- Atomic single commit

### §5.4 Q3 Adjudication: SEPARATE PR for SRE-002 step-level optimizations
Counters Potnia recommendation. Rationale:
- Blast-radius minimization wins under cross-fleet-ramp pressure
- Substrate-readiness gate: post-Path-B `.test_durations` regen pending; step-level optimizations need refreshed substrate
- Maintainer review velocity: focused PR reviewable in 1-2 cycles vs bundled 3-5
- §9.7 attribution clarity: separate PR makes ROI attribution clean

Routing: Sprint-4 OR new `HANDOFF-sre-to-eunomia-2026-05` artifact; defer-watch register entry.

## §6 Sub-sprint C Charter — Sprint-3 Close

### §6.1 Post-merge measurement protocol (observability-engineer)

After A4 ramp completes (8 satellites green) AND B2 lands:
- Capture 5 successful main-branch CI runs post-Path-B
- Extract per-job timings via `gh run view --json jobs`
- Compute slowest-shard p50 + per-job avg/p95
- Compare against BASELINE §4 (447s slowest-shard p50 pre-engagement)
- Compare against post-Sprint-2 supplement §8 measurement (514s)

### §6.2 Verdict adjudication

Apply parent Sprint-2 charter §9.2 promotion criterion:
- **PASS-CLEAN-PROMOTION**: ≥20% CI shard p50 reduction vs BASELINE (post ≤358s) → amend supplement §9.7 + amend parent VERDICT-test-perf frontmatter `overall_verdict: PASS-WITH-FLAGS → PASS-CLEAN`
- **PASS-WITH-FLAGS-PRESERVED**: <20% reduction → amend supplement §9.7 documenting Path B outcome; promotion path remains open
- **PASS-WITH-FLAGS-AMPLIFIED**: regression direction (post >447s) → flag-amplification; route to incident-commander

### §6.3 Telos declaration close (per §1.4)

Sub-sprint C cannot close without `.know/telos/sprint3-path-b-2026-04-30.md` materialized. Verification of `verified_realized` field deferred to verification_deadline (Sprint-3 close + 14d).

### §6.4 Sprint-3 PR + HANDOFF amendment

PR mirrors PR #44/#45/#46/#47/#48 pattern. HANDOFF-eunomia-to-sre amended:
- SRE-001: closed (prior)
- SRE-002: closed (Path B landed; step-level optimizations routed to Q3 separate PR per §5.4)
- SRE-003: closed (prior, ADR-010)
- SRE-004: closed (prior)
- SRE-005: closed (this sprint, ADR-013)

## §7 Cross-Repo Coordination Protocol

### §7.1 (AMENDED) Authorization gate LIFTED
Per §1.1: user authority grant 2026-04-30T18:31Z lifts the gate. No further pre-flight authorization required for `autom8y/autom8y-workflows` PR authoring this sprint.

### §7.2 SHA-pinning ramp (INHERITED parent §7.2)
Per-satellite SHA-pin upgrade with 1-CI-run-per-satellite verification. Reversible via `git revert` on consuming satellite repo.

### §7.3 Chaos-engineer canary (INHERITED parent §7.3)
Canary satellite: autom8y-asana. 3-run sample. Abort criteria per §4.5.

### §7.4 Stall-detection + escalation (NEW)
If cross-repo PR review velocity stalls (>72hr without maintainer engagement):
- Document in `.sos/wip/sre/STALL-LOG-sprint3-2026-04-30.md`
- Escalate to user for direct maintainer-coordination authorization
- HALT downstream sub-sprints (A3 + A4) pending PR merge

## §8 Inviolable Constraints

### §8.1 Pattern-6 drift-audit re-dispatch
Re-run drift-audit at every specialist dispatch (A1, A2, A3, A4, B1, B2, C).

### §8.2 SCAR cluster preservation (≥47 operational)
Pre/post each commit:
- `pytest -m scar --collect-only -q | tail -3` shows ≥47
- `pytest -m scar --tb=short` exits 0
- Divergence triggers halt-on-fail per §8.3

### §8.3 Halt-on-fail discipline
- ANY local test failure → HALT, surface, route
- ANY out-of-scope file modification → HALT, refuse
- ANY drift-audit failure → HALT, re-validate
- ANY cross-fleet satellite CI failure during ramp → HALT ramp, route to incident-commander

### §8.4 Authority boundaries

**In-scope** (Sprint-3 may modify):
- `autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml` (cross-repo PR)
- `.github/workflows/test.yml` (autom8y-asana SHA-pin update)
- `.github/workflows/*.yml` (new hadolint workflow if §5.3 warrants)
- `.hadolint.yaml` (config; new file)
- `.pre-commit-config.yaml` (hadolint hook addition; if pre-commit in use)
- `.ledge/decisions/*.md` (ADR-012 + ADR-013)
- `.ledge/reviews/HANDOFF-eunomia-to-sre-2026-04-29.md` (Sub-sprint C amendment)
- `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` (§9.7 amendment)
- `.ledge/reviews/VERDICT-test-perf-2026-04-29.md` (frontmatter mutation IF PASS-CLEAN-PROMOTION)
- `.know/telos/sprint3-path-b-2026-04-30.md` (NEW file per §1.4)
- `.sos/wip/sre/*.md` (audit + log artifacts)

**Out-of-scope** (MUST refuse and route):
- Production code (`src/autom8_asana/**`) — route /eunomia or /10x-dev
- Test code (`tests/**`) — route /hygiene
- `pyproject.toml` beyond markers section
- Other `.know/` files except `.know/telos/sprint3-path-b-2026-04-30.md`

### §8.5 Atomic-revertibility per commit
Each Sub-sprint commit independently revertible. Cross-repo PR is single revertible unit.

### §8.6 "Taking no prisoners" entrenchment
User authority does NOT relax §8 inviolables. Halt-route preferred over "best-effort merge" under uncertainty. Cross-repo PR with measured wallclock evidence is principled; speculative ramp without canary validation is forbidden.

## §9 Verdict-Discharge Contract

### §9.1 Required artifacts
- `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` §9.7 appended (Sub-sprint C close-gate)
- `.ledge/decisions/ADR-012-path-b-runner-tier-and-worker-count-2026-04-30.md` (Sub-sprint A close-gate)
- `.ledge/decisions/ADR-013-sre-005-hadolint-2026-04-30.md` (Sub-sprint B close-gate)
- `.know/telos/sprint3-path-b-2026-04-30.md` (per §1.4 HARD prerequisite)

### §9.2 Promotion criterion (per parent §9.2)
≥20% CI shard p50 reduction vs BASELINE 447s → PASS-CLEAN-PROMOTION + parent VERDICT mutation. Else PASS-WITH-FLAGS-PRESERVED.

### §9.3 Sprint-3 fails without §9.1 artifacts
Engagement does not close cleanly without all 4 artifacts authored. This is the structural close-gate.

## §10 Cross-Rite Routing Recommendations (At-Close)

| Target rite | Items | Rationale |
|---|---|---|
| **/sre Sprint-4** (future) | SRE-002 step-level optimizations (uv-cache, mypy incremental, dependency-install parallelism, step ordering) | Q3(b) separate PR routing |
| **/eunomia v3** | Lambda-context fixture gap (HYG-002 Phase 2 surfaced) + paginator-Protocol gap (Phase 1 surfaced) | accumulated drift signals from prior engagements |
| **/hygiene Phase 3+** | ~3,000 unspec'd mock sites (HYG-002 multi-sprint campaign continues) | continued in-flight HANDOFF |
| **/arch** (consultation) | Fleet-wide runner-tier policy decision IF Path B reveals systematic patterns | architecture-altitude question |

## §11 Open Verification-Phase Risks

### §11.1 Cross-repo PR maintainer review velocity (HIGH per Potnia §7)
The autom8y-workflows reusable workflow is high-traffic substrate. Maintainer review may surface back-compat concerns. **Mitigation**: §4.4 schema preserves back-compat (`default: 'standard'` and `default: 0` = `auto`); §4.4 matrix self-test exercises both default paths.

### §11.2 8-satellite ramp queue-depth pathology (MEDIUM, NEW)
`ubuntu-latest-large` has different queue-depth profile than `ubuntu-latest`. Concurrent fleet ramp may saturate. **Mitigation**: §4.6 staging order + 1-CI-run-per-satellite hard cap; chaos-engineer abort criterion §4.5(c) catches cycle-time degradation.

### §11.3 hadolint maintainer-velocity asymmetry (LOW)
hadolint upstream may release rule changes that flag previously-passing Dockerfiles. **Mitigation**: pin `hadolint/hadolint-action@v3.x.x` (specific patch); renovate-bot or manual update on rule-corpus refresh.

### §11.4 SCAR cluster operational coverage gap under Path B topology (LOW)
Path B changes test-execution topology (8-vCPU; possibly different `-n N`). SCAR markers may behave differently. **Mitigation**: parent §8.2 invariant; full-suite halt-on-fail is primary structural net.

### §11.5 Probe-CI runner-minute budget reset (LOW, NEW)
Sprint-2 closed at 0/20 probe-CI consumed. Sprint-3 inherits 20-budget; A1 audit + A4 canary 3-runs + 8-satellite ramp = ~12 CI runs. **Mitigation**: 8-run buffer; further runs require user authorization.

### §11.6 Authority-shift inscription drift (LOW, NEW)
§1.1 LIFT recorded HERE but NOT in parent §7.1. **Mitigation**: §3.2 APPENDED entry + ADR-012 authority chain inscription.

### §11.7 Branch hygiene (LOW, INHERITED)
`.worktrees/` + uncommitted platform mods. **Mitigation**: explicit-paths-only `git add` discipline.

### §11.8 Cross-fleet ramp partial-success ambiguity (MEDIUM, NEW)
8-satellite ramp may succeed at 7/8. **Mitigation**: §6.3 PASS-WITH-FLAGS-PRESERVED is structural fallback; partial-fleet ramp blocks PASS-CLEAN binary threshold; observability-engineer §9.7 documents per-satellite outcomes.

### §11.9 Telos declaration authoring time-cost (LOW, NEW)
`telos-integrity-ref` schema is non-trivial (30-60 min budget). **Mitigation**: halt-route preferred over fabricated verification methods.

## §12 Source Manifest

| Role | Artifact | Path |
|---|---|---|
| HANDOFF (incoming) | eunomia → /sre | `.ledge/reviews/HANDOFF-eunomia-to-sre-2026-04-29.md` |
| Parent VERDICT (discharge target) | PASS-WITH-FLAGS | `.ledge/reviews/VERDICT-test-perf-2026-04-29.md` |
| Supplement (§9.7 amendment target) | PASS-WITH-FLAGS-PRESERVED | `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` |
| BASELINE | 447s anchor | `.ledge/reviews/BASELINE-test-perf-2026-04-29.md` |
| Parent Sprint-2 charter | governing predecessor | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md` |
| Sprint-2 ADRs | Path B framing | `.ledge/decisions/ADR-008-runner-sizing-no-lever-2026-04-30.md`, `ADR-009-xdist-worker-count-no-local-override-2026-04-30.md`, `ADR-010-shard-expansion-stay-at-4-2026-04-30.md` |
| M-16 source | VERDICT-eunomia §7 | `.ledge/reviews/VERDICT-eunomia-final-adjudication-2026-04-29.md` |
| Reusable workflow PR target | satellite-ci-reusable.yml | `autom8y/autom8y-workflows/.github/workflows/satellite-ci-reusable.yml:393` (runner) + `:527-528` (worker) |
| A1 audit (TO BE AUTHORED) | Path B audit | `.sos/wip/sre/AUDIT-path-b-cross-repo-2026-04-30.md` |
| B1 audit (TO BE AUTHORED) | SRE-005 audit | `.sos/wip/sre/AUDIT-sre-005-dockerfile-2026-04-30.md` |
| ADR-012 (TO BE AUTHORED) | Path B decision | `.ledge/decisions/ADR-012-path-b-runner-tier-and-worker-count-2026-04-30.md` |
| ADR-013 (TO BE AUTHORED) | hadolint decision | `.ledge/decisions/ADR-013-sre-005-hadolint-2026-04-30.md` |
| Telos declaration (§1.4 prerequisite) | Sprint-3 telos | `.know/telos/sprint3-path-b-2026-04-30.md` |
| Branch | Sprint-3 working | `sre/sprint3-path-b-2026-04-30` (cut from main@e3b5749e) |
| THIS artifact | governing Sprint-3 charter | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint3.md` |

---

*Authored 2026-04-30 by Pythia consultation + main-thread materialization. MODERATE evidence-grade per `self-ref-evidence-grade-rule`. Pattern-6 drift-audit discipline carried forward verbatim from parent Sprint-2 §3.1 and great-grandparent perf §4.1. User authority grant 2026-04-30T18:31Z LIFTS parent §7.1 cross-repo gate; multi-satellite SHA-pinning ramp + chaos-engineer canary survive as operational discipline. Q1(a) BUNDLED PR; Q2(a) HADOLINT with B1 confirmation gate; Q3(b) SEPARATE PR for step-level optimizations; Q4 8-satellite ramp + 3-criterion abort. Telos-integrity gate at §1.4 is HARD prerequisite for Sub-Sprint C close. Phase transition recommendation: PLAN → SUB-SPRINT-A1 + B1 (parallel; first action: platform-engineer dispatched for both audit phases).*
