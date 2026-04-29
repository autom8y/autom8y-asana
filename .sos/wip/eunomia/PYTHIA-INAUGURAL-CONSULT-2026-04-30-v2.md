---
artifact_id: PYTHIA-INAUGURAL-CONSULT-2026-04-30-v2
schema_version: "1.0"
type: design
artifact_type: charter
slug: v2-2026-04-30
rite: eunomia
initiative: auth-isolation-defect-fix-and-verdict-re-discharge
complexity: MODULE
phase_posture: PLAN
session_id: session-20260430-001257-0f7223d6
parent_sessions:
  - session-20260429-161352-83c55146 (parent perf engagement)
  - session-20260429-190827-422f0668 (parent /sre engagement; auto-wrapped)
parent_charters:
  - PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf
  - PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre
authored_by: pythia (consultative throughline) + main-thread (materialization)
authored_at: 2026-04-30
evidence_grade: MODERATE
self_grade_ceiling_rationale: "Pythia self-authoring v2 charter; MODERATE per self-ref-evidence-grade-rule"
authoring_style: prescriptive-charter
governance_status: governing
inherits_from:
  - PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf (parent perf charter; constraint inheritance)
  - PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre (parent /sre charter; verdict-discharge contract inheritance)
  - HANDOFF-sre-to-eunomia-2026-04-29 (incoming sprint scope)
  - VERDICT-test-perf-2026-04-29-postmerge-supplement (failure evidence + hypothesis)
status: proposed
---

# PYTHIA INAUGURAL CONSULT — Eunomia v2 (Auth-Isolation Fix + Verdict Re-Discharge)

## §1 Telos Restatement

User invocation (verbatim, capture timestamp 2026-04-29T22:10Z):

> *"Proceed heeding an updated Potnia consult with the incoming handoff rite to
> remain optimally engage on this procession initiative with strong prompt and
> context engineering throughout the autonomous agentic coordinated /sprint
> workflow(s) until the next demanded rite switch — requiring me to restart CC."*

User has authorized full autonomous agentic execution through engagement close. Halt only on hard-fail conditions per §8 inviolable constraints.

**Charter altitude**: this is the *v2 successor* engagement that closes the auth-isolation gap discovered by the SRE-001 measurement protocol. Without this v2, the parent VERDICT-test-perf carries PASS-WITH-FLAGS forward indefinitely AND PR #44 cannot merge cleanly.

**Anchor-return question** (per `telos-integrity-ref §5`): does this initiative have a named user-visible outcome? **YES** — three: (a) PR #44 CI shard 1/4 turns green, (b) parent VERDICT promotes PASS-WITH-FLAGS → PASS-CLEAN, (c) BASELINE substrate corrected for future engagements.

## §2 Engagement Scope

| Field | Lock |
|---|---|
| Track | test/fixture surface + verdict-discharge documentation |
| Complexity | **MODULE** (smaller than parent INITIATIVE; bounded fix scope) |
| Phase posture | **PLAN** (this charter precedes V2-001-A executor dispatch) |
| Sprint structure | single sprint, sequential: V2-001 → V2-002 (V2-003 parallel-able) |
| Lens overlay | parent eunomia 7-category schema **plus**: Auth-Isolation Discipline + Verdict-Discharge Discipline (v2-specific) |
| Authority | bounded to test/fixture surface; production-code OUT-OF-SCOPE except parent-charter `core/system_context.py` allowance (now EXHAUSTED — see R-NEW-1) |
| Inviolable constraints | drift-audit re-dispatch, full-suite preservation, refusal posture (§8) |

## §3 Inheritance Audit (per `inherited-charter-audit-discipline`)

### §3.1 INHERITED (preserved verbatim from parent charters)
- **Pattern-6 drift-audit re-dispatch** (parent perf §4.1, /sre §8.1): re-run drift-audit at planner AND executor altitudes for V2-001 mutation surface
- **SCAR cluster preservation** (parent perf §8.1): full-suite passing pre/post each commit
- **Halt-on-fail discipline** (parent perf §8.3): atomic single-commit-per-change; halt + route on any failure
- **Refusal posture** (parent perf §3.2 + /sre §8.4): out-of-scope items HALT and route, do not absorb scope creep
- **Drift-audit-discipline skill** (parent /sre §8.1): synthesis-altitude clause applies

### §3.2 APPENDED (new at v2 altitude)
- **Reproduce-first protocol** (§5): 30-60min investigation budget BEFORE fix-design to confirm hypothesis vs reveal alternate root cause
- **Hybrid N=2 verdict-discharge** (§7): cost-disciplined sample size for re-discharge measurement; falls back to N=5 if direction marginal
- **Production-code halt-route protocol** (§6): explicit HALT + route to /10x-dev if root cause traces beyond test surface
- **Lens overlay**: Auth-Isolation Discipline + Verdict-Discharge Discipline (test-fixture isolation rigor + measurement-anchored close-gate)

### §3.3 DELTA'd (none expected)
Parent perf charter's authority surface remains valid for what already landed (the 6 CHANGE commits + close-state docs). v2 EXTENDS the engagement; does not contradict parent constraints.

## §4 Sprint v2 Charter

### §4.1 EUN-V2-001 — Fix AUTH-ISOLATION-DIST-LOAD-REGRESSION (CRITICAL, blocking)

Three-task chain: V2-001-A (reproduce + investigate) → V2-001-B (implement + commit fix) → V2-001-C (PR CI verification).

**Failure evidence** (per supplement §3 + §6.4):
- Test: `tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503`
- Assertion: `401 == 503` (auth returning 401 Unauthorized when test expects 503 Service Unavailable)
- Determinism: confirmed N=2 (363.7s + 365.6s, 0.5% delta)
- Branch-introduced: main HEAD `e27cbf2d` shows all 4 shards green; PR #44 specifically shows the regression

**Hypothesis** (supplement §6.4): T1A's worker-local `_reset_registry` refactor + T1D's `--dist=load` switch interact with `routes/resolver.py` auth dependency in a way `--dist=loadfile` masked by co-locating auth-fixture and resolver tests on the same xdist worker. Under load mode, they distribute, leaving the resolver-test worker un-seeded.

### §4.2 EUN-V2-002 — Re-discharge §9.2 verdict supplement (HIGH, blocked-by V2-001)

Two-task chain: V2-002-A (re-discharge supplement) → V2-002-B (promote parent VERDICT if PASS-CLEAN).

**Verdict-promotion contract** (parent perf charter §9 inheritance): if pytest-internal delta ≥40% of CI shard reduction → PASS-CLEAN-PROMOTION → parent VERDICT frontmatter `overall_verdict: PASS-WITH-FLAGS → PASS-CLEAN`.

### §4.3 EUN-V2-003 — BASELINE §4 attribution correction (MEDIUM, parallel-able)

Author corrigendum supplement OR amend BASELINE-test-perf-2026-04-29.md §4 with empirical SRE-001 measurement (~93/7 pytest-vs-infrastructure split, NOT estimated ~21/79). Update VERDICT §11.1 risk-discharge framing. Update HANDOFF-eunomia-to-sre SRE-002 scope-shrink note.

## §5 Investigation Protocol for EUN-V2-001 (Q1 adjudication: REPRODUCE-FIRST)

### §5.1 Reproduce-first methodology

V2-001-A executor MUST follow this sequence BEFORE proposing any fix:

1. **Local reproduction** (10-15 min):
   ```bash
   pytest -n 4 --dist=load tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503 --tb=short
   ```
   Confirm assertion `401 == 503` fires. If reproduction FAILS locally (test passes): the defect is environment-specific to CI; widen scope to capture full local environment fingerprint.

2. **Fixture-chain trace** (15-25 min):
   - Read `tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete` test body and surrounding class
   - Read `tests/unit/api/conftest.py` (likely has `app` + `authed_client` fixtures per parent test-coverage knowledge)
   - Read `tests/conftest.py:97-204` (root fixtures: `mock_http`, `auth_provider`, `_bootstrap_session`, `reset_all_singletons`)
   - Map the fixture dependency graph for the failing test
   - Identify which fixture sets up the auth state that's missing under load distribution

3. **Hypothesis confirmation** (10-20 min):
   - If trace confirms supplement §6.4 hypothesis (auth fixture co-location dependency): proceed to V2-001-B fix design
   - If trace reveals different root cause within test surface: document, route to V2-001-B with adjusted scope
   - If trace reveals ROOT CAUSE IN PRODUCTION CODE (e.g., `routes/resolver.py` reads global state initialized only when auth fixture and resolver test co-locate): HALT per §6 production-code halt-route protocol

### §5.2 Investigation deliverable
Author `.sos/wip/eunomia/INVESTIGATION-auth-isolation-2026-04-30.md` (~50-100 lines) with:
- Reproduction confirmation (PASS/FAIL + environment notes)
- Fixture chain diagram (text or mermaid)
- Root cause adjudication: TEST-SURFACE-CONFIRMED / PRODUCTION-CODE-REQUIRED / DEFER
- Recommended fix surface (specific file:line targets)

### §5.3 Drift-audit at consult dispatch (Pattern-6 carry-forward)
Re-confirmed at v2 charter authoring (2026-04-30T00:12Z):
- PR #44 still OPEN at https://github.com/autom8y/autom8y-asana/pull/44
- Branch `eunomia/test-perf-2026-04-29` HEAD `56569466` (close-state docs commit)
- 9 commits ahead of main `523067af`
- Failing test still: `tests/unit/api/test_routes_resolver.py::TestResolveDiscoveryIncomplete::test_discovery_incomplete_returns_503` (verified via supplement §3.2)
- Drift status: CONFIRMED CLEAN

## §6 Production-Code Halt-Route Protocol (Q3 adjudication)

If V2-001-A investigation determines root cause is in production code (`src/autom8_asana/api/routes/resolver.py` or other src file beyond the parent charter's `core/system_context.py` allowance):

### §6.1 HALT V2-001-B
Do NOT proceed to fix implementation. Authority boundary preserved per §3.1 inheritance + parent perf §3.2.

### §6.2 Author HANDOFF-eunomia-to-10x-dev
Path: `.ledge/reviews/HANDOFF-eunomia-to-10x-dev-2026-04-30.md`. Type: execution. Includes:
- Full investigation findings (link to INVESTIGATION-auth-isolation artifact)
- Specific production-code surface requiring change
- Test-surface fix that would be applied IF authorization extended
- /10x-dev execution criteria (preserve auth-state-management contract; SCAR cluster intact)

### §6.3 Continue V2-002 + V2-003 anyway
V2-002 supplement amendment is NOT blocked on production-code fix; it can document the deferred-promotion state with explicit /10x-dev dependency. V2-003 BASELINE correction is independent of fix.

### §6.4 Engagement closes at PASS-WITH-FLAGS-CARRIED
Parent VERDICT does NOT promote to PASS-CLEAN; the supplement §8 documents the production-code dependency; promotion-on-merge contract: when /10x-dev fix lands and re-runs CI, supplement amends to POST-PRODUCTION-FIX-MEASUREMENT and parent VERDICT promotes.

## §7 Verdict-Discharge Contract (Q2 adjudication: HYBRID-N=2)

### §7.1 Sample-size protocol
After V2-001 lands and CI shard 1/4 passes:
- **Trigger 1 manual rerun** via `gh run rerun` (or natural push trigger if subsequent commits land)
- Wait for that rerun to complete
- Adjudicate: if both attempts (original-post-fix + 1 rerun) show clear direction (>40% pytest delta in both) → PASS-CLEAN-PROMOTION at N=2
- If marginal (one attempt >40%, other <40%) → trigger 3 more reruns to reach N=5; promote/carry per N=5 sample
- If both attempts <40% delta → PASS-WITH-FLAGS-CARRIED + SRE-002 scope confirmed

### §7.2 Escape valve
If sample-variance flag fires (CI runs vary >20% in absolute timings): widen sample to N=5 minimum; document variance in supplement §8.

### §7.3 Supplement amendment surface
Append §8 "POST-FIX MEASUREMENT" section to existing supplement (do NOT re-author entire artifact). §8 contains:
- N achieved
- Per-job avg/p50/p95 across post-fix sample
- Delta vs BASELINE §4 (corrected per V2-003 if landed)
- Delta vs PR #44 attempt-1 pre-fix measurement
- Promotion adjudication rationale

### §7.4 Parent VERDICT mutation under PASS-CLEAN-PROMOTION
If V2-002 adjudicates PASS-CLEAN-PROMOTION:
1. Frontmatter: `overall_verdict: "PASS-WITH-FLAGS" → "PASS-CLEAN"`
2. Frontmatter: append `promotion: { date: 2026-04-30, supplement: VERDICT-test-perf-2026-04-29-postmerge-supplement, criterion: §9.3-clean }`
3. §1 amendment: append "Promoted PASS-CLEAN on 2026-04-30 per supplement §8 measurement (N=X; pytest delta Y%)"
4. §9.5 residual-routing: amend to reflect SRE-002 scope-shrink (per V2-003 BASELINE correction)
5. `flags_summary` field (if present): mark §9.2 flag as DISCHARGED with cross-ref to supplement §8

## §8 Inviolable Constraints (mirror parent §8 with v2-altitude reformulations)

### §8.1 Pattern-6 drift-audit re-dispatch
Per §3.1: re-run drift-audit at executor dispatch for V2-001-A (verify failing test still fails as documented), V2-001-B (verify fix file:line targets unchanged from V2-001-A investigation), V2-002 (verify CI run state matches expected post-fix), V2-002-B (verify parent VERDICT frontmatter shape pre-mutation).

### §8.2 Full-suite preservation
Each v2 commit gates on local `pytest -n 4 --dist=load tests/unit/` 100% pass. Push only after local green. Halt on any local failure.

### §8.3 Halt-on-fail discipline
- ANY local test failure pre or post commit → HALT, surface, route to next-investigation
- ANY out-of-scope file modification surfaces → HALT, refuse, surface
- ANY drift-audit failure between sprint dispatches → HALT, re-validate substrate

### §8.4 Authority boundaries

**In-scope** (v2 may modify):
- `tests/conftest.py` (root fixtures)
- `tests/unit/api/conftest.py` (API conftest with `authed_client`/`app` fixtures)
- `tests/unit/api/test_routes_resolver.py` (the failing test file itself, if assertion-level fix warranted)
- `.sos/wip/eunomia/*.md` (v2 artifacts: investigation, charter)
- `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` (V2-002-A amendment)
- `.ledge/reviews/VERDICT-test-perf-2026-04-29.md` (V2-002-B promotion mutation IF PASS-CLEAN)
- `.ledge/reviews/BASELINE-test-perf-2026-04-29.md` OR new supplement (V2-003 correction)

**Out-of-scope** (MUST refuse and route):
- Production code (`src/autom8_asana/**`) — including `routes/resolver.py` (HALT-route to /10x-dev per §6)
- `core/system_context.py` — parent allowance EXHAUSTED (see R-NEW-1); further changes require explicit user re-authorization
- CI shape (`.github/workflows/`) — /sre territory
- `pyproject.toml` — already touched at line 113 by perf engagement; further changes route to /sre
- Mock spec= adoption / MockTask consolidation — /hygiene HYG-001/002/003

### §8.5 Atomic-revertibility per commit
Each v2 commit independently revertible via `git revert HEAD --no-edit`. PR review can adjudicate v2 commits independently of parent close-state commits.

## §9 Cross-Rite Handoff Cleanup at Close

### §9.1 HANDOFF-sre-to-eunomia lifecycle
At v2 close: transition `.ledge/reviews/HANDOFF-sre-to-eunomia-2026-04-29.md` frontmatter `status: in_progress → completed`, `handoff_status: accepted → discharged`, append `discharged_at: <ISO timestamp>`, append `discharge_artifacts: [...]` listing supplement amendment + parent VERDICT promotion + V2-003 correction.

### §9.2 HANDOFF-RESPONSE-eunomia-to-sre authorship
Author `.ledge/reviews/HANDOFF-RESPONSE-eunomia-to-sre-2026-04-30.md` acknowledging discharge of EUN-V2-001 + V2-002 + V2-003. Includes:
- Confirmation that parent VERDICT promoted (or carried with /10x-dev dependency)
- BASELINE correction surface
- /sre Sprint-2 scope-revision (SRE-002 ~6% headroom; SRE-003/004/005 unchanged)
- Re-engagement timing (post v2 close)

### §9.3 If §6 production-code halt fires: HANDOFF-eunomia-to-10x-dev
Per §6.2 — separate cross-rite handoff for production-code scope.

### §9.4 /sos wrap or rite preservation
Per user authority grant: "until the next demanded rite switch — requiring me to restart CC". Engagement runs to natural close on this rite. /sos wrap fires at task #27 completion.

## §10 Open Verification-Phase Risks

### §10.1 Investigation may reveal production-code scope (MEDIUM)
V2-001-A may surface root cause in `routes/resolver.py` or other src file beyond parent allowance. **Mitigation**: §6 production-code halt-route protocol pre-defined; PASS-WITH-FLAGS-CARRIED close path preserves engagement value.

### §10.2 CI rerun cost discipline (LOW)
N=2 minimum minimizes CI cost; escape valve to N=5 if marginal. **Mitigation**: §7.1 sample-size protocol; clear direction at N=2 unblocks PASS-CLEAN immediately.

### §10.3 BASELINE correction may surface further inversions (LOW)
V2-003 may discover the BASELINE §4 was wrong in OTHER ways beyond the 21/79 split. **Mitigation**: V2-003 corrigendum is targeted to the specific inversion identified; broader BASELINE re-audit deferred to future engagement.

### §10.4 R-NEW-1: core/system_context.py parent allowance EXHAUSTED (LOW)
If V2-001 investigation reveals further worker-local refactor needed there, executor cannot mutate without re-authorization. **Mitigation**: §5 investigation surfaces this pre-fix; halt-route fires before mutation.

### §10.5 R-NEW-2: parent VERDICT mutation field nuance (LOW)
§9.5 residual is INVERTED by SRE-001 §4.1, not just discharged. Risk of sloppy frontmatter under autonomous flow. **Mitigation**: §7.4 prescribes exact field-level mutations; executor MUST follow verbatim.

### §10.6 R-NEW-3: PR review surface increase (LOW)
Branch already at 9 commits; v2 stacks on top. **Mitigation**: §8.5 atomic-revertibility preserved per-commit; PR review can adjudicate v2 commits independently.

## §11 Source Manifest

| Role | Artifact | Absolute path |
|---|---|---|
| HANDOFF (incoming, accepted) | sre → eunomia | `.ledge/reviews/HANDOFF-sre-to-eunomia-2026-04-29.md` |
| Failure evidence + hypothesis | SRE-001 supplement | `.ledge/reviews/VERDICT-test-perf-2026-04-29-postmerge-supplement.md` |
| Parent perf charter | constraint inheritance | `.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md` |
| Parent /sre charter | /sre charter inheritance | `.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-29-sre.md` |
| Parent VERDICT (V2-002-B mutation target) | promotion target | `.ledge/reviews/VERDICT-test-perf-2026-04-29.md` |
| Parent BASELINE (V2-003 correction target) | substrate target | `.ledge/reviews/BASELINE-test-perf-2026-04-29.md` |
| Parallel /sre HANDOFF | cross-coordination | `.ledge/reviews/HANDOFF-eunomia-to-sre-2026-04-29.md` |
| Parallel /hygiene HANDOFF | cross-coordination | `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md` |
| V2-001-A investigation deliverable (TO BE AUTHORED) | reproduce-first artifact | `.sos/wip/eunomia/INVESTIGATION-auth-isolation-2026-04-30.md` |
| THIS artifact (governing v2 charter) | inaugural consult | `.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-30-v2.md` |

## §12 Phase Transition

**PLAN → SPRINT-V2.** First action: dispatch rationalization-executor for Task V2-001-A (reproduce + investigate per §5) with reproduce-first protocol, drift-audit attestation, and §6 halt-route preserved.

After V2-001-A executor reports findings: main thread adjudicates (a) V2-001-B fix-design dispatch IF investigation confirms test-surface root cause, OR (b) §6 production-code halt-route IF investigation surfaces production-code dependency.

V2-002 + V2-003 sequence per §4.2 + §4.3.

---

*Authored 2026-04-30 by Pythia consultation + main-thread materialization.
MODERATE evidence-grade per `self-ref-evidence-grade-rule`. Pattern-6 drift-audit
discipline carried forward from VERDICT-eunomia-final-adjudication §5 and parent
perf charter §4.1. User authority grant for autonomous agentic execution
documented at §1; halt conditions enumerated at §6 + §8. Q1 = REPRODUCE-FIRST,
Q2 = HYBRID-N=2, Q3 = halt-route to /10x-dev. Phase transition recommendation:
PLAN → SPRINT-V2 (first action: V2-001-A executor dispatch per §5).*
