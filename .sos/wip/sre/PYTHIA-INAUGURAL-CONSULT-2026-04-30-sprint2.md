---
artifact_id: PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2
schema_version: "1.0"
type: design
artifact_type: charter
slug: sprint2-2026-04-30
rite: sre
initiative: sre-sprint2-discharge-handoff-residuals
complexity: INITIATIVE
phase_posture: PLAN
session_id: session-20260430-115401-513947b2
parent_session: session-20260429-190827-422f0668
parent_charter: PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre
authored_by: pythia (consultative throughline) + main-thread (materialization)
authored_at: 2026-04-30
evidence_grade: MODERATE
self_grade_ceiling_rationale: "Pythia self-authoring on /sre Sprint-2 charter; MODERATE per self-ref-evidence-grade-rule"
authoring_style: prescriptive-charter
governance_status: governing
inherits_from:
  - PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre (parent /sre Sprint-1 charter)
  - PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf (grandparent eunomia perf charter)
  - PYTHIA-INAUGURAL-CONSULT-2026-04-30-v2 (cousin v2 charter — adjudication patterns)
  - VERDICT-test-perf-2026-04-29-postmerge-supplement §8.4 (empirical scope inversion)
  - HANDOFF-eunomia-to-sre-2026-04-29 (in_progress; SRE-001 discharged)
status: proposed
---

# PYTHIA INAUGURAL CONSULT — /sre Sprint-2 (sprint2-2026-04-30)

## §1 Telos Restatement

User invocation (verbatim, capture timestamp 2026-04-30T09:52Z):

> *"Max rigor and max vigor sustained throughout taking no prisoners"*
>
> *"...autonomous agentic coordinated /sprint workflows until the next demanded
> rite switch — requiring me to restart CC."*

User has authorized full-pantheon orchestration through engagement close. Halt only on hard-fail conditions per §8 inviolable constraints. The "taking no prisoners" intensification clause entrenches §8 — no scope-creep absorption, no soft-close, no theater.

**Charter altitude**: this is the *Sprint-2* of an in_progress HANDOFF. The structural successor that closes the §8.4 sub-route residuals and discharges the parent VERDICT's PASS-WITH-FLAGS-CARRIED state via supplement §9 amendment.

**Anchor-return question** (per `telos-integrity-ref §5`): three named user-visible outcomes verifiable by rite-disjoint measurement: (a) ADR-NNN documenting 002a runner-sizing disposition, (b) measurable CI shard p50 reduction post-engagement (target ≥20%), (c) supplement §9 amendment promoting parent VERDICT or routing residuals to operational backlog.

**Scope-inversion declaration**: the original SRE-002 thesis (~353s/447s = 79% non-pytest infrastructure overhead) was empirically falsified by supplement §8.4. Actual: pytest is ~93.3% of CI shard wallclock; infrastructure is ~6.7%. CI runner core-count is the binding constraint. Sprint-2 inherits the §8.4 sub-routes (002a/b/c) as the authoritative SRE-002 scope.

## §2 Engagement Scope

| Field | Lock |
|---|---|
| Track | CI infrastructure runner-sizing + xdist tuning + post-merge governance |
| Complexity | **INITIATIVE** (multi-sub-route; pantheon orchestration) |
| Phase posture | **PLAN** (this charter precedes Sprint-2A specialist dispatch) |
| Sprint structure | Sprint-2A (BLOCKING) → Sprint-2B (parallel) → Sprint-2C (parallel) → Sprint-2D (DEFER per Q3) |
| Pantheon | potnia (orchestrator) \| platform-engineer (002a/c, 003, 004 execution) \| chaos-engineer (002a canary on §4.4 escalation) \| observability-engineer (post-engagement re-measurement + supplement §9 amendment) |
| Authority | in-rite full; cross-repo PR RESERVED with §7.1 pre-flight gate |
| Inviolable constraints | drift-audit re-dispatch, SCAR preservation (now ≥47 operational), refusal posture (§8) |

## §3 Inheritance Audit (per `inherited-charter-audit-discipline`)

### §3.1 INHERITED (preserved verbatim from parent + grandparent + cousin)
- **Pattern-6 drift-audit re-dispatch** (parent /sre §3.1, grandparent perf §4.1): re-run drift-audit at planner AND executor altitudes for every Sprint-2 specialist dispatch
- **SCAR cluster preservation** (parent perf §8.1, NOW operational post-HYG-001): full-suite passing pre/post each commit; `pytest -m scar --collect-only -q` must report ≥47 collected
- **Halt-on-fail discipline** (parent perf §8.3): atomic single-commit-per-change; halt + route on any failure
- **Refusal posture** (parent /sre §8.4, parent perf §3.2): out-of-scope items HALT and route, do not absorb scope creep
- **Drift-audit-discipline skill** (parent /sre §8.1): synthesis-altitude clause applies
- **Cross-repo coordination protocol** (parent /sre §7): pre-flight authorization gate; SHA-pinning during ramp; chaos-engineer canary requirement
- **Verdict-discharge contract** (parent /sre §9): observability-engineer authors §9 amendment; promotion criterion structurally falsifiable

### §3.2 APPENDED (new at Sprint-2 altitude)
- **Scope-shift to §8.4 sub-routes**: 002a/002b/002c REPLACE original SRE-002 scope (infrastructure thesis falsified)
- **Full-pantheon orchestration**: 4-agent active dispatch surface (potnia + 3 specialists), exceeds Sprint-1's single observability-engineer pattern
- **Per-sub-route ADR discipline**: each sub-route closes with either (a) commit + verification, or (b) ADR documenting NO-LEVER decision; no sub-route closes silently
- **Probe-CI runner-minute hard cap** (§11.2): 20 probe-CI-runs total across Sprint-2A/2B/2C; cost-discipline gate
- **"Taking no prisoners" intensification clause**: §8 inviolables are non-negotiable; user authorization grant does NOT relax §8

### §3.3 DELTA'd (none expected)
Parent /sre and grandparent perf charters remain authoritative for what landed previously. This Sprint-2 EXTENDS the engagement; does not contradict.

## §4 Sprint-2A Charter — SRE-002a Runner-Sizing Investigation (BLOCKING)

### §4.1 Hypothesis (to confirm or refute)
Per supplement §8.4: CI 2-vCPU runners thrash `pytest -n 4 --dist=load` (4 workers contending for 2 cores). Local 8+ vCPUs parallelize cleanly (-49% achieved). The supplement hypothesis is that runner core-count is the binding constraint on CI shard wallclock.

### §4.2 Reproduce-first protocol (timebox 2-4hr; mirrors v2 §5.1)
1. **Confirm runner tier**: `gh api /repos/autom8y/autom8y-asana/actions/runs/<run-id>` for recent successful main runs; inspect runner labels (ubuntu-latest = 2-vCPU free; ubuntu-latest-large = 4-vCPU; etc.)
2. **Probe worker count effect**: open a draft PR adjusting `test.yml` `test_parallel`/xdist `-n` value — test 1, 2, 4 workers — measure shard p50 across 3 runs each
3. **Cost-benefit math**: GitHub Actions runner pricing × runtime delta; compute $/run for each option
4. **Adjudicate**: pick lever (or combination) with best wallclock × cost ROI
5. **Author investigation artifact** at `.sos/wip/sre/INVESTIGATION-runner-sizing-2026-04-30.md` (200-300 lines)

### §4.3 Outcome adjudications (4 possible)
- **RUNNER-TIER-UPGRADE**: switch to ubuntu-latest-large or equivalent; measurable wallclock gain expected
- **WORKER-COUNT-REDUCTION**: keep current runner; reduce `-n 4` to `-n 2` (matches vCPU); reduces thrashing
- **HYBRID**: combine runner upgrade + worker count tuning
- **NO-LEVER**: current 4-worker on 2-vCPU is local-optimum given cost; document via ADR

### §4.4 Escalation criterion (Q1 adjudication = a; bounded escalation to b)
Default path: spike-and-decide; ONE remediation commit + close.

**Escalate to full Sprint-2A treatment** (with chaos-engineer canary + cross-repo PR) ONLY if:
1. Investigation requires modification to `autom8y/autom8y-workflows` reusable workflow (cross-fleet impact)
2. Investigation surfaces multi-satellite coupling (other autom8y repos affected by same change)
3. Investigation surfaces production-code defect (route to /eunomia v3 or /10x-dev per §10)

If none of (1-3) fire: close at single commit OR ADR + ADR-driven Sprint-2A close. No chaos-engineer dispatch needed.

### §4.5 Specialist dispatch
- **platform-engineer** authors investigation + remediation (or ADR if NO-LEVER)
- **observability-engineer** captures probe-branch wallclock measurements rite-disjoint from platform-engineer authoring
- **chaos-engineer** STANDBY only (fires on §4.4 escalation 1-3)

## §5 Sprint-2B Charter — SRE-002b Worker-Count Tuning + SRE-002c Shard-Balance Refresh

Both blocked-by Sprint-2A close; parallel after.

### §5.1 SRE-002b — xdist worker-count tuning
- platform-engineer probes `--dist=load -n auto` vs `--dist=load -n 2` vs current empirically (3-run sample each)
- Atomic single-commit if win is measurable (≥10% shard p50 reduction)
- ADR if no measurable win

### §5.2 SRE-002c — shard-balance refresh
- Regenerate `.test_durations` under post-2A topology (different runner-count or worker-count changes the math)
- platform-engineer commits refreshed durations file
- Verification: shard variance ≤15% (down from BASELINE ~30%)

## §6 Sprint-2C Charter — SRE-003 Shard Expansion + SRE-004 Coverage Job (parallel post-2B)

### §6.1 SRE-003 — 4→8 shard expansion sizing
- platform-engineer empirical sizing under post-Sprint-2B topology
- Decision: stay-at-N / 6 / 8 with ADR rationale
- Apply if: aggregate wallclock reduction × added-runner-cost favorable

### §6.2 SRE-004 — Post-merge aggregate coverage job
- Author new workflow job: `--cov=src/autom8_asana --cov-fail-under=80` single-shard post-merge
- Independent of 002 outcomes; can land regardless of Sprint-2B
- Closes GLINT-003 coverage-gate-theater debt

## §7 Cross-Repo Coordination Protocol

### §7.1 Pre-flight authorization gate (Q2 adjudication = c default; a/b reserved)
**Default path (Q2c)**: close Sprint-2 with autom8y-asana-local fixes + ADRs. Cross-repo work is RESERVED, not defaulted.

**Escalate to cross-repo PR** ONLY if §4.4 escalation criteria fire. If escalation fires:
1. Verify GitHub permissions: `gh repo view autom8y/autom8y-workflows` (must succeed)
2. Identify workflow maintainers via CODEOWNERS or repo settings
3. Surface to user for explicit authorization grant (per parent /sre §7.1)
4. Document authorization in commit message
5. Pin SHAs in consuming satellites during ramp (parent /sre §7.2)
6. Chaos-engineer canary validation per parent /sre §7.3

### §7.2 Q2 sub-options (if escalation fires)
- **Q2a (immediate)**: open cross-repo PR on 002a finding
- **Q2b (bundled)**: wait for 002b/002c to consolidate; bundle single PR

Recommend Q2b if multiple sub-routes need cross-repo changes (reduces fleet-coordination overhead).

## §8 Inviolable Constraints (mirror parent §8 with Sprint-2-altitude reformulations)

### §8.1 Pattern-6 drift-audit re-dispatch
Per §3.1: re-run drift-audit at every specialist dispatch.

### §8.2 SCAR cluster preservation (NOW OPERATIONAL post-HYG-001)
HYG-001 codified the `scar` marker; ≥47 SCAR tests now operationally selectable. Sprint-2 inherits this as a structural net:
- Pre-commit: `pytest -m scar --collect-only -q | tail -3` (must show ≥47)
- Post-commit: same command (must still show ≥47)
- Pre/post commit: `pytest -m scar --tb=short` exits 0
- ANY divergence triggers halt-on-fail per §8.3

### §8.3 Halt-on-fail discipline
- ANY local test failure pre or post commit → HALT, surface, route
- ANY out-of-scope file modification surfaces → HALT, refuse
- ANY drift-audit failure between sprint dispatches → HALT, re-validate substrate
- ANY probe-CI failure that ISN'T the targeted regression → HALT, investigate

### §8.4 Authority boundaries

**In-scope** (Sprint-2 may modify):
- `.github/workflows/test.yml` (autom8y-asana repo)
- `.ledge/decisions/*.md` (ADR authoring per §3.2 per-sub-route discipline)
- `.test_durations` (regeneration per SRE-002c/003)
- `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` (§9 amendment per Sprint-2 close)
- `.ledge/reviews/VERDICT-test-perf-2026-04-29.md` (frontmatter promotion IF §9 amendment criterion met)
- `autom8y/autom8y-workflows/*.yml` via cross-repo PR (RESERVED per §7.1; gate fires only on §4.4 escalation)

**Out-of-scope** (MUST refuse and route):
- Production code (`src/autom8_asana/**`) — route /eunomia or /10x-dev
- Test code (`tests/**`) — route /hygiene
- `pyproject.toml` — already touched at line 113 by perf engagement
- SCAR markers (`@pytest.mark.scar`) — HYG-001 already landed
- `.know/` files (knowledge substrate; not Sprint-2 surface)

### §8.5 Atomic-revertibility per commit
Each Sprint-2 commit independently revertible via `git revert HEAD --no-edit`.

### §8.6 "Taking no prisoners" entrenchment
User authorization for autonomous /sprint workflows does NOT relax §8 inviolables. The intensification clause STRENGTHENS §8: no soft-close, no scope absorption, no theater. Halt-route is preferred over "best-effort merge" under any uncertainty.

## §9 Verdict-Discharge Contract (Sprint-2 close-gate)

### §9.1 Required artifact mutation
After Sprint-2A/B/C land (before Sprint-2D consideration):
- observability-engineer triggers 5 successful CI runs on main (post-merge of Sprint-2 PR)
- Captures per-job p50/avg/p95 across the 5-run sample
- Computes delta vs BASELINE §4 (slowest-shard p50 = 447s pre-engagement)
- Computes delta vs supplement §8 (slowest-shard p50 = 514s post-T1+T2+V2-fix)

### §9.2 Promotion criterion
- **PASS-CLEAN-PROMOTION**: ≥20% CI shard p50 reduction vs BASELINE 447s (i.e., post ≤358s) → amend supplement §9 with promotion recommendation + amend parent VERDICT frontmatter `overall_verdict: PASS-WITH-FLAGS → PASS-CLEAN`
- **PASS-WITH-FLAGS-PRESERVED**: <20% reduction → amend supplement §9 documenting partial-discharge + route remaining sub-route residuals to operational backlog (NOT perpetually-open)
- **PASS-WITH-FLAGS-AMPLIFIED**: regression direction (post >447s) → flag-amplification; route to /eunomia v3 re-engagement

### §9.3 Supplement amendment surface
Append to existing supplement (do NOT re-author):
```markdown
## §9 SPRINT-2 POST-DISCHARGE MEASUREMENT
- Sample: N=5 (run-ids: ...)
- HEAD: <main-merge-sha after Sprint-2 PR>
- Per-shard timings table
- Delta vs BASELINE 447s + delta vs §8 514s
- Promotion adjudication
- Routing implications
```

### §9.4 Without §9 amendment: engagement FAILS
Sprint-2 does NOT close cleanly without observability-engineer §9 authorship. This is the structural close-gate.

## §10 Cross-Rite Routing Recommendations (At-Close)

| Target rite | Items | Rationale |
|---|---|---|
| **/hygiene** (resume) | HYG-002 (mock spec= adoption), HYG-003 (MockTask consolidation), HYG-004 (parametrize-promote DEFER-T3A) | Already in-flight HANDOFF; user-explicit return path post-Sprint-2 |
| **/hygiene** (new) | DEFER-SRE-005 (M-16 Dockerfile pattern enforcement) | Q3(b) adjudication; tooling decision more native to /hygiene than /sre |
| **/eunomia v3** (re-engagement) | Only if 002a investigation surfaces production-code defect requiring further refactor | Route via new HANDOFF-sre-to-eunomia-2026-04-30 if fires |
| **/arch** (consultation) | Only if 002a surfaces architecture-altitude question (e.g., fleet-wide runner-tier policy) | Out-of-/sre-rite design decisions |
| **/10x-dev** | None expected | — |

## §11 Open Verification-Phase Risks

### §11.1 Investigation-scope expansion (002a → cross-fleet) (MEDIUM)
§4.4 escalation criterion is the gate; if 002a finding requires cross-repo work, Sprint-2 timeline doubles. **Mitigation**: §7.1 pre-flight authorization preserves user-in-the-loop control.

### §11.2 Probe-CI runner-minute budget (MEDIUM, NEW)
Sprint-2A probe = 3 worker-count configs × 3 runs = 9 CI runs minimum; potential Sprint-2B/2C reruns add more. **Mitigation**: hard cap **20 probe-CI-runs total** across Sprint-2; further runs require explicit user authorization. Tracked in execution log.

### §11.3 Runner-pool capacity surprises (LOW)
GitHub Actions runner availability varies by tier; ubuntu-latest-large may have queue depth. **Mitigation**: §4.2 step 1 confirms runner labels; if queue depth issue, document in ADR.

### §11.4 Supplement §9 amendment authority preservation (LOW)
Future engagements may further amend supplement §8 before Sprint-2 close. **Mitigation**: Pattern-6 drift-audit at §9 authoring confirms supplement state pre-amendment.

### §11.5 SCAR cluster operational coverage gap (LOW, NEW)
HYG-001 closed at ≥47 markers but some regression tests may not be classified. **Mitigation**: full-suite halt is primary structural net; SCAR is secondary safety check.

### §11.6 Cousin v2 substrate drift (LOW, NEW)
Cousin v2 engagement (closed) may receive supplement-amendment activity from other rites. **Mitigation**: Pattern-6 re-dispatch at every Sprint-2 specialist invocation.

### §11.7 Branch hygiene — concurrent worktrees + uncommitted platform mods (LOW, NEW)
`.worktrees/` directory + uncommitted modifications to `.knossos/sync/state.json`, `.know/aegis/baselines.json`, `aegis-report.json` per session onset git status. **Mitigation**: explicit-paths-only `git add` discipline; no `git add -A`/`-.`; allowlist-based commit scope.

## §12 Source Manifest

| Role | Artifact | Absolute path |
|---|---|---|
| HANDOFF (incoming, in_progress) | eunomia → /sre | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-eunomia-to-sre-2026-04-29.md` |
| Parent VERDICT (discharge target) | PASS-WITH-FLAGS | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/VERDICT-test-perf-2026-04-29.md` |
| Supplement (§8.4 sub-route opening; empirical scope inversion) | PASS-WITH-FLAGS-CARRIED at v2-002 | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` |
| BASELINE (measurement source; pre-engagement p50 = 447s anchor) | §4 = CI per-job anchor | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/BASELINE-test-perf-2026-04-29.md` |
| Parent /sre Sprint-1 charter | governing predecessor | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre.md` |
| Grandparent eunomia perf charter | structural origin | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md` |
| Cousin v2 charter (Q1/Q2/Q3 adjudication patterns) | adjacent engagement | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-30-v2.md` |
| Sprint-2 first-deliverable target (TO BE AUTHORED) | INVESTIGATION-runner-sizing | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/sre/INVESTIGATION-runner-sizing-2026-04-30.md` |
| Sprint-2 close-gate target (TO BE AUTHORED) | supplement §9 amendment | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` (§9 amended in place) |
| Branch | Sprint-2 working branch | `sre/sprint2-residuals-2026-04-30` (cut from main@a7af2457) |
| THIS artifact (governing Sprint-2 charter) | inaugural Sprint-2 consult | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md` |

---

*Authored 2026-04-30 by Pythia consultation + main-thread materialization.
MODERATE evidence-grade per `self-ref-evidence-grade-rule`. Pattern-6
drift-audit discipline carried forward verbatim from parent /sre Sprint-1
charter §3.1 and grandparent eunomia perf charter §4.1. User authority
grant for "max rigor max vigor taking no prisoners" autonomous /sprint
workflows recorded at §1; intensification clause entrenches §8 inviolables
at §8.6. Q1(a) spike-and-decide; Q2(c) close at local + ADR; Q3(b) defer
SRE-005 to /hygiene backlog. Phase transition recommendation: PLAN →
SPRINT-2A (first action: SRE-002a reproduce-first protocol per §4.2;
specialist dispatch: platform-engineer; chaos-engineer standby for §4.4
escalation only).*
