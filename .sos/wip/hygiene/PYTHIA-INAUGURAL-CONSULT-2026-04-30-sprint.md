---
artifact_id: PYTHIA-INAUGURAL-CONSULT-2026-04-30-hygiene-sprint
schema_version: "1.0"
type: design
artifact_type: charter
slug: sprint-2026-04-30
rite: hygiene
initiative: hygiene-sprint-discharge-handoff-residuals
complexity: INITIATIVE
phase_posture: PLAN
session_id: session-20260430-131833-8c8691c1
predecessor_session: session-20260430-105520-40481a0e
parent_handoff: HANDOFF-eunomia-to-hygiene-2026-04-29
sibling_charters:
  - PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2 (sre/Sprint-2)
  - PYTHIA-INAUGURAL-CONSULT-2026-04-30-v2 (eunomia/v2)
grandparent_charter: PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf
authored_by: pythia (consultative throughline) + main-thread (materialization)
authored_at: 2026-04-30
evidence_grade: MODERATE
self_grade_ceiling_rationale: "Pythia self-authoring; MODERATE per self-ref-evidence-grade-rule"
authoring_style: prescriptive-charter
governance_status: governing
inherits_from:
  - HANDOFF-eunomia-to-hygiene-2026-04-29 (parent — governing item list)
  - PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2 (sibling — sub-sprint structure pattern)
  - PYTHIA-INAUGURAL-CONSULT-2026-04-30-v2 (cousin — adjudication patterns)
  - PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf (grandparent — §8 inviolables)
  - PLAN-hyg-001 + AUDIT-VERDICT-hyg-001 (immediate-predecessor — /task pattern)
status: proposed
---

# PYTHIA INAUGURAL CONSULT — /hygiene Sprint (sprint-2026-04-30)

## §1 Telos Restatement

User invocation (verbatim, capture timestamp 2026-04-30T13:18Z):

> *"max rigor max vigor taking no prisoners"* autonomous /sprint workflows until next rite switch — same posture as /sre Sprint-2 just landed (PR #46 merged 2026-04-30T11:08Z). Discharge HYG-002 + HYG-003 + HYG-004 from in-flight HANDOFF-eunomia-to-hygiene.

User has authorized full-pantheon orchestration through engagement close. Halt only on hard-fail conditions per §8 inviolable constraints. The "taking no prisoners" intensification clause entrenches §8 — no scope-creep absorption, no soft-close, no theater.

**Engagement-chain context**: this is the structural *test-surface* successor to /sre Sprint-2 (CI-shape close, PR #46). HYG-001 (SCAR codification) discharged via PR #45 immediate-predecessor. HYG-002/003/004 remain open in the parent HANDOFF.

**Charter altitude**: this is the inaugural Sprint of an in_progress HANDOFF accepted at 2026-04-30T08:55:20Z by predecessor session-20260430-105520-40481a0e (now stale per moirai note — Sub-sprint D wraps it). Sub-sprint A/B/C/D structure mirrors sibling /sre Sprint-2A/2B/2C/2D pattern verbatim.

**Anchor-return question** (per `telos-integrity-ref §5`): three named user-visible outcomes verifiable by rite-disjoint measurement: (a) root mock fixtures + 1 high-density consumer carry `spec=` (HYG-002 Phase 1 surface certification); (b) 11 bespoke MockTask classes consolidated into superset canonical (HYG-003 full discharge); (c) `tests/unit/test_config_validation.py` 28-test cluster collapses to ~4 parametrized cases with assertion-specificity preserved (HYG-004 Phase 1 pattern-validation).

## §2 Engagement Scope

| Field | Lock |
|---|---|
| Track | Test/fixture surface — mock spec= adoption (Phase 1) + MockTask consolidation + parametrize-promote |
| Complexity | **INITIATIVE** (multi-sub-sprint; pantheon orchestration) |
| Phase posture | **PLAN** (this charter precedes Sub-sprint A code-smeller dispatch) |
| Sprint structure | A (HYG-002 Phase 1) → B (HYG-003 full) → C (HYG-004 Phase 1) → D (close) |
| Pantheon | potnia (orchestrator) \| code-smeller (HYG-002 scoping) \| architect-enforcer (per-sub-sprint plans) \| janitor (execution) \| audit-lead (verification) |
| Authority | in-rite full on test surface; refusal posture entrenched on production code + CI shape |
| Inviolable constraints | drift-audit re-dispatch, SCAR preservation (≥47 operational), refusal posture (§8) |
| Branch | `hygiene/sprint-residuals-2026-04-30` (cut from main@4396d099 = PR #46 merge) |

## §3 Inheritance Audit (per `inherited-charter-audit-discipline`)

### §3.1 INHERITED (preserved verbatim)
- Pattern-6 drift-audit re-dispatch (grandparent perf §4.1, sibling /sre §3.1)
- SCAR cluster preservation NOW OPERATIONAL (≥47 markers post-HYG-001)
- Halt-on-fail discipline (grandparent perf §8.3, sibling /sre §8.3)
- Refusal posture (grandparent perf §3.2, sibling /sre §8.4)
- Drift-audit-discipline skill synthesis-altitude clause
- Atomic-revertibility per commit (grandparent perf §8, sibling /sre §8.5)
- HANDOFF item priority order: HYG-002 (medium) → HYG-003 (low) → HYG-004 (low)

### §3.2 APPENDED (new at /hygiene Sprint altitude)
- Per-sub-sprint ADR discipline (mirror sibling /sre §3.2)
- HYG-001 plan+audit pattern (~200-line plan + ~200-line audit per /task)
- smell-detection methodology for Sub-sprint A (Skill("smell-detection") preload)
- Audit-lead verification gate per HYG-001 pattern
- Predecessor-session wrap discipline (Sub-sprint D)
- "Taking no prisoners" intensification clause (§8.6)

### §3.3 DELTA'd (none expected)
This charter EXTENDS the engagement; does not contradict.

## §4 Sub-sprint A Charter — HYG-002 Phase 1 Mock spec= Adoption (BLOCKING)

### §4.1 Q1 Adjudication: (a) root fixtures + 1 top-density file

**Locked path**: root fixtures at `tests/conftest.py:98-123` (mock_http, logger, config, auth_provider) + `tests/integration/test_lifecycle_smoke.py` (133 mocks — highest-density consumer).

**Rationale**: root fixtures unlock spec= dispersion across all consumers automatically. Pairing with the highest-density consumer in the SAME sub-sprint validates dispersion empirically — if root-fixture spec'ing surfaces interface drift, the 133-mock consumer surfaces it densely.

### §4.2 Reproduce-first protocol (timebox 2-4hr per HYG-001 pattern)

1. **code-smeller** scopes mock surface with `Skill("smell-detection")` preload; enumerates all `MagicMock(...)` sites with canonical-type binding candidates per site
2. **architect-enforcer** plans (~200 lines at `.sos/wip/hygiene/PLAN-hyg-002-phase1-2026-04-30.md`): ordered spec= application list; canonical-type-resolution-failure halt criteria; SCAR preservation gate; assertion-specificity rules
3. **janitor** executes: atomic single commit; tests pass post-commit; SCAR ≥47
4. **audit-lead** verifies (~200 lines at `.sos/wip/hygiene/AUDIT-VERDICT-hyg-002-phase1-2026-04-30.md`): per-AC ledger; interface-drift findings filed as separate sub-issues per HYG-002 AC 5

### §4.3 Outcome adjudications (3 possible)
- **PHASE-1-CLEAN-CLOSE**: root + lifecycle_smoke spec'd; tests pass; no drift; SCAR preserved
- **PHASE-1-CLOSE-WITH-DRIFT-FINDINGS**: drift filed as sub-issues per HYG-002 AC 5; Phase 1 still closes
- **NO-LEVER**: canonical types unresolvable for some sites; ADR partial close

## §5 Sub-sprint B Charter — HYG-003 MockTask Consolidation (sequential post-A)

### §5.1 Q2 Adjudication: (a) strict superset extend

**Locked path**: extend canonical at `tests/_shared/mocks.py:10` to SUPERSET of all 11 bespoke variants' attributes; migrate consumers.

**Rationale**: parent HANDOFF AC 3 explicitly directs this; avoids "multiple canonicals" anti-pattern. Bloat acceptable on test surface.

### §5.2 Reproduce-first protocol
1. **architect-enforcer** plans (~200 lines): inventory of all 11 bespoke schemas; computed superset; per-consumer migration delta; ordered execution
2. **janitor** executes as 1-3 atomic commits (canonical extension + consumer migration)
3. **audit-lead** verifies: all 11 bespoke removed; consumers migrated; convention codified in `.know/conventions.md` per AC 5; SCAR preserved
4. **Convention codification** (AC 5): append to `.know/conventions.md` — *"New tests requiring MockTask MUST import from tests/_shared/mocks; bespoke redefinition forbidden."*

### §5.3 Outcome adjudications
- **CONSOLIDATION-CLEAN-CLOSE**: 11 → 1 canonical; convention codified
- **PARTIAL-CONSOLIDATION-CLOSE**: subset has irreconcilable conflicts; ADR documents
- **NO-OP-CLOSE**: schema conflicts fundamental; route to /eunomia or /10x for production-side unification

## §6 Sub-sprint C Charter — HYG-004 Phase 1 Parametrize-Promote (parallel post-B-or-A)

### §6.1 Q3 Adjudication: (a) test_config_validation.py first

**Locked path**: `tests/unit/test_config_validation.py` (lines 43-71 + 110-138, 28-test cluster → ~4 parametrized = 86% reduction; 694-line file = smallest of the 4).

**Rationale**: smallest file lowers risk; largest single-file reduction validates pattern. Remaining 3 adversarial files (tier1, tier2, batch) carry forward as Phase 2 multi-sprint residuals.

### §6.2 Reproduce-first protocol
1. **architect-enforcer** plans (~200 lines): cluster enumeration with file:line; parametrize-target value-range table; assertion-specificity-preservation rules; coverage-delta verification step
2. **janitor** executes: atomic commit; tests pass; coverage delta ≥0
3. **audit-lead** verifies: cluster collapsed; specificity preserved (sample 3 cases); coverage ≥0; SCAR ≥47

### §6.3 Outcome adjudications
- **PHASE-1-CLEAN-CLOSE**: 28 → ~4 parametrized; coverage ≥0
- **PARAMETRIZE-PARTIAL-CLOSE**: some cases resist collapse; ADR + remaining stay non-parametrized
- **NO-OP-CLOSE**: cluster non-collapsible; ADR; route as DEFER-HYG-004-residual

## §7 Sub-sprint D Charter — Close PR + HANDOFF Lifecycle + Predecessor-Session Wrap

### §7.1 PR authoring
PR title: `hygiene(sprint): test-surface residuals — HYG-002 Phase 1 + HYG-003 + HYG-004 Phase 1 [Sprint-2026-04-30]`. Pattern mirrors PR #44/#45/#46. Branch: `hygiene/sprint-residuals-2026-04-30`. Base: main@4396d099.

### §7.2 HANDOFF amendment
Amend `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md`:
- HYG-002: `in_progress` (Phase 1 closed; Phase 2 multi-sprint residual)
- HYG-003: `closed` (full discharge)
- HYG-004: `in_progress` (Phase 1 closed; 3 of 4 files remain)

### §7.3 Predecessor-session wrap
Predecessor session-20260430-105520-40481a0e wrapped via `Task(moirai, "wrap session-20260430-105520-40481a0e — superseded by Sprint-2026-04-30 close")`.

### §7.4 Cross-rite routing recommendations at-close
See §10.

## §8 Inviolable Constraints (mirror grandparent + sibling)

### §8.1 Pattern-6 drift-audit re-dispatch
Re-run drift-audit at every specialist dispatch.

### §8.2 SCAR cluster preservation (NOW OPERATIONAL post-HYG-001)
- Pre/post commit: `pytest -m scar --collect-only -q | tail -3` shows ≥47
- Pre/post commit: `pytest -m scar --tb=short` exits 0
- ANY divergence → halt-on-fail per §8.3

### §8.3 Halt-on-fail discipline
- ANY local test failure pre or post commit → HALT, surface, route
- ANY out-of-scope file modification → HALT, refuse
- ANY drift-audit failure → HALT, re-validate
- ANY mock-spec interface drift NOT filed as separate sub-issue → HALT, refuse silent absorption

### §8.4 Authority boundaries

**In-scope**:
- `tests/conftest.py` (root fixture region — HYG-002 Phase 1)
- `tests/integration/test_lifecycle_smoke.py` (HYG-002 Phase 1 high-density consumer)
- `tests/_shared/mocks.py` (HYG-003 canonical extension)
- 11 bespoke MockTask consumer files (HYG-003 migration)
- `tests/unit/test_config_validation.py` (HYG-004 Phase 1)
- `.know/conventions.md` (HYG-003 AC 5 convention)
- `.ledge/decisions/*.md` (ADR per §3.2)
- `.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md` (Sub-sprint D amendment)

**Out-of-scope** (MUST refuse and route):
- Production code (`src/autom8_asana/**`) — route /eunomia or /10x-dev
- CI shape (`.github/workflows/`) — route /sre
- `pyproject.toml` beyond markers section
- SCAR markers — HYG-001 already landed
- `.know/test-coverage.md` — defer to /know rite
- Other `.know/` files except `.know/conventions.md`

### §8.5 Atomic-revertibility per commit
Each sub-sprint commit independently revertible.

### §8.6 "Taking no prisoners" entrenchment
User authorization does NOT relax §8 inviolables. The intensification clause STRENGTHENS §8: no soft-close, no scope absorption, no theater. Halt-route preferred over "best-effort merge". Mock-spec interface drift findings (HYG-002 AC 5) MUST be filed as separate sub-issues — silent absorption is the precise scope-creep failure mode this clause forbids.

## §9 Verdict-Discharge Contract (Sprint close-gate)

### §9.1 Per-sub-sprint discharge
After EACH sub-sprint:
- janitor commit lands on branch
- audit-lead verdict at `.sos/wip/hygiene/AUDIT-VERDICT-hyg-NNN-{phase}-2026-04-30.md` (~200 lines per HYG-001 pattern)
- SCAR ≥47 preserved
- Per-AC ledger in audit-lead verdict (PASS/FAIL/DEFER with file:line evidence)

### §9.2 Sprint-close PR gate
Sub-sprint D opens PR; embeds:
- Per-sub-sprint commit-SHA + verdict-artifact-path table
- HANDOFF item discharge state
- Multi-sprint residual surface for HYG-002 Phase 2 + HYG-004 Phase 2
- Cross-rite routing recommendations

### §9.3 Without close PR + HANDOFF amendment: engagement FAILS
Sprint does NOT close cleanly without (i) close PR landing on main, (ii) HANDOFF amendment per §7.2, (iii) predecessor-session wrap per §7.3.

## §10 Cross-Rite Routing Recommendations (At-Close)

| Target rite | Items | Rationale |
|---|---|---|
| **/hygiene** (re-engagement, future sprint) | HYG-002 Phase 2 (3,000+ unspec'd sites — multi-sprint campaign) | Continued in-flight HANDOFF |
| **/hygiene** (re-engagement, future sprint) | HYG-004 Phase 2 (3 of 4 adversarial files: tier1, tier2, batch) | DEFER-T3A residual |
| **/sre** (deferred from Sprint-2) | SRE-005 (M-16 Dockerfile) | Already-routed at /sre Sprint-2 close |
| **/eunomia v3** (re-engagement) | Only if HYG-002 spec'ing surfaces production-code defect | Route via new HANDOFF if fires |
| **/10x-dev** | Only if HYG-003 superset surfaces production-side schema unification need | Route as new HANDOFF if fires |
| **/arch** (consultation) | Only if HYG-002 surfaces architecture-altitude question | Out-of-/hygiene design decision |

## §11 Open Verification-Phase Risks

### §11.1 Mock spec= surfaces interface drift (MEDIUM, EXPECTED)
HYG-002 Phase 1 spec'ing is *designed* to surface interface drift — that is the SCAR-026 mitigation thesis. Per §8.6 + AC 5, drift findings file as separate sub-issues. **Mitigation**: route via cross-rite HANDOFF (per §10).

### §11.2 MockTask superset bloat boundary (LOW)
Strict superset may produce 30+ attributes. **Mitigation**: superset documented in `.know/conventions.md`; future schema-unification routed to /10x-dev per §10.

### §11.3 Parametrize-promotion assertion-specificity preservation (MEDIUM)
Collapse may inadvertently weaken assertion specificity. **Mitigation**: architect plan §6.2 step 1 explicit rules; audit-lead samples 3 cases for manual inspection.

### §11.4 SCAR collection count regression (LOW)
Test-file modifications could inadvertently strip a `@pytest.mark.scar` decorator. **Mitigation**: §8.2 pre/post-commit verification gate.

### §11.5 Coverage delta regression on HYG-004 Phase 1 (LOW)
Parametrize collapse can reduce branch coverage. **Mitigation**: HYG-004 AC 6 hard gate; janitor includes coverage report check.

### §11.6 Predecessor-session wrap timing (LOW, NEW)
PR open must precede moirai wrap dispatch to preserve session-context lineage. **Mitigation**: §7.3 sequence — PR open → moirai dispatch → wrap.

### §11.7 Branch hygiene (LOW, INHERITED)
Concurrent worktrees + uncommitted platform mods. **Mitigation**: explicit-paths-only `git add` per §8.4.

### §11.8 HYG-002 root-fixture spec= cascade (LOW, NEW)
Root-fixture spec'ing affects every test importing affected fixtures. If interface drift surfaces, blast radius could span hundreds of test files. **Mitigation**: §4.3 PHASE-1-CLOSE-WITH-DRIFT-FINDINGS adjudication explicitly anticipates this; Phase 1 still closes on root + 1 file regardless of cascade scope discovered.

## §12 Source Manifest

| Role | Artifact | Absolute path |
|---|---|---|
| HANDOFF (incoming, in_progress) | eunomia → /hygiene | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.ledge/reviews/HANDOFF-eunomia-to-hygiene-2026-04-29.md` |
| Sibling /sre Sprint-2 charter | engagement-pattern template | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/sre/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint2.md` |
| Cousin v2 charter | adjudication patterns | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-30-v2.md` |
| Grandparent perf charter | structural origin | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/eunomia/PYTHIA-INAUGURAL-CONSULT-2026-04-29-perf.md` |
| Immediate-predecessor HYG-001 plan + audit | predecessor reference | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/hygiene/PLAN-hyg-001-scar-codification-2026-04-30.md` + `AUDIT-VERDICT-hyg-001-2026-04-30.md` |
| HYG-002 substrate (mock surface enumeration) | substrate | `.know/test-coverage.md` |
| HYG-003 canonical | substrate | `tests/_shared/mocks.py:10` |
| HYG-002 root-fixture target | substrate | `tests/conftest.py:98-123` |
| HYG-002 Phase 1 high-density consumer | Q1a target | `tests/integration/test_lifecycle_smoke.py` |
| HYG-004 Phase 1 target | Q3a target | `tests/unit/test_config_validation.py` |
| SCAR cluster substrate | post-HYG-001 operational | `.know/scar-tissue.md` |
| Sub-sprint A first-deliverable target (TO BE AUTHORED) | architect plan | `.sos/wip/hygiene/PLAN-hyg-002-phase1-2026-04-30.md` |
| Sub-sprint B first-deliverable target (TO BE AUTHORED) | architect plan | `.sos/wip/hygiene/PLAN-hyg-003-2026-04-30.md` |
| Sub-sprint C first-deliverable target (TO BE AUTHORED) | architect plan | `.sos/wip/hygiene/PLAN-hyg-004-phase1-2026-04-30.md` |
| Branch | Sprint working branch | `hygiene/sprint-residuals-2026-04-30` (from main@4396d099) |
| THIS artifact (governing /hygiene Sprint charter) | inaugural Sprint consult | `/Users/tomtenuta/Code/a8/repos/autom8y-asana/.sos/wip/hygiene/PYTHIA-INAUGURAL-CONSULT-2026-04-30-sprint.md` |

---

*Authored 2026-04-30 by Pythia consultation + main-thread materialization. MODERATE evidence-grade per `self-ref-evidence-grade-rule`. Pattern-6 drift-audit discipline carried forward verbatim from grandparent eunomia perf charter §4.1 and sibling /sre Sprint-2 charter §3.1. SCAR preservation invariant operational at ≥47 markers post-HYG-001 (PR #45). Per-sub-sprint ADR + audit-lead-verdict discipline appended at §3.2. User authority grant for "max rigor max vigor taking no prisoners" autonomous /sprint workflows recorded at §1; intensification clause entrenches §8 inviolables at §8.6. Q1(a) root fixtures + lifecycle_smoke.py; Q2(a) strict superset extend; Q3(a) test_config_validation.py first. Phase transition recommendation: PLAN → SUB-SPRINT-A (first action: HYG-002 Phase 1 reproduce-first protocol per §4.2; specialist dispatch sequence: code-smeller → architect-enforcer → janitor → audit-lead).*
