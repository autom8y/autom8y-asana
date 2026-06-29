---
type: review
status: accepted
evidence_grade: MODERATE
evidence_note: >
  SELF-CAP MODERATE, stated per G-CRITIC: eunomia is grading surfaces partly
  authored by eunomia-adjacent processions (CHANGE-005b aggregate coverage gate,
  CHANGE-001 nightly forcing function, and the E2 inventories themselves were
  produced inside this governance arc). Self-ref-evidence-grade-rule ceiling
  applies to every grade and ruling below. Same-satellite evidence is
  NON-promoting throughout (O-2 precedent). MODERATE is the ceiling, not the floor.
station: E3 (entropy-assessor)
rite: eunomia
procession: Pre-Clear External Corroboration & Governance Custody
inputs:
  - .ledge/reviews/EUNOMIA-E2a-test-surface-inventory-2026-06-11.md
  - .ledge/reviews/EUNOMIA-E2b-pipeline-inventory-2026-06-11.md
  - .ledge/specs/THROUGHLINE-integration-boundary-fidelity-2026-06-10.md
  - .ledge/reviews/EUNOMIA-INTERIM-CORROBORATION-keystone-day1-2026-06-11.md
authored: 2026-06-11
constraints: "NO merges from this station; 06-18 STRONG reserved; rule narrow."
---

# EUNOMIA E3 — Grades and Custody — 2026-06-11

## Executive Summary

The saga's test accumulation is in unusually good health: the 7 focal files are
clean on every adversarial axis (0 log-string-primary-proof, 0 xfail, mock index
1:1), and whole-surface mock discipline holds at the 1:1 canonical index. The
weakest link is CI pin/version hygiene: the autom8y monorepo's
terraform-apply-reusable.yml carries six node20-era action pins with a 2026-06-16
deprecation deadline that lands two days BEFORE soak-clear (06-18) — the asana
prod TF-apply chain could brownout exactly when clear-day needs it. Overall
grade is therefore **C** by weakest-link, with an explicit bump-now ruling on
E2b#1 (merge-safe-now surface, fires nothing on merge). Custody: three new
primitives are registered as CANDIDATES at honest N=1 each — One-Gate Invariant
(NEW candidate, sibling of integration-boundary-fidelity), iris pipe-smoke
(technique-grade), and the soak-sentinel schema (with MF-1/2/3 as registered
caveats). No promotions; same-satellite evidence rules narrow.

---

## JOB (a) — Health Report Card (weakest-link model)

| # | Category | Grade | Justifying findings (IDs) |
|---|----------|-------|---------------------------|
| 1 | Test organization | **B** | F-1 MEDIUM (test_workspace_switching.py 8/8 dead-skip skeleton, 148 LOC, zero passing tests ever) + F-2 MEDIUM (epoch-tagged test_routes_query_project_section_rows_sprint2.py, live prototype confusing vs non-suffixed sibling). Structure otherwise sound: 543 files in coherent directory taxonomy, 16-level conftest hierarchy, xfail=0 whole-surface. |
| 2 | Mock/fixture discipline | **A-** | MockTask proliferation index 1:1 (1 canonical def, 0 bespoke redefs — HYG-003 holds; SCAR-EA-003: this is A-band). F-3 LOW (_InMemoryStorage ×3, _DegradedBuildStrategy ×2 — boilerplate-only, honest altitude-layering confirmed by E2a §5) and F-4 LOW (_frame helper copy-paste ×3) cost the minus. Saga focal files: 1 local fixture, 42 mock-sites, all transport-boundary stubs. |
| 3 | Adversarial/agent accumulation | **A-** | One epoch-tag signal (F-2). 17 adversarial-named files ruled project naming DISCIPLINE, not accumulation (7+ subdomains, multi-sprint, 0 qa/ dirs). No monotonic-growth signal; no consolidation debt. Structural signals only — no authorship attributed [AP-06]. |
| 4 | Coverage governance | **A-** | Gate REAL at both altitudes (aggregate 80% in test.yml via satellite-ci-reusable + post-merge --cov-fail-under=80); config-vs-enforcement gap: none. Minus from E2b#4 LOW-MED: post-merge-coverage.yml .coverage upload missing include-hidden-files → diagnostic artifact silently hollow — the SAME scar class (autom8y-workflows#24) re-manifesting in a sibling workflow; gate correctness unaffected. |
| 5 | CI safety-config | **B** | Permissions 12/12 (100%, all at least job-level explicit); concurrency 8/12 (67%); timeouts 7/12 (58%) but the only genuine gap is dockerfile-lint.yml (E2b#8 LOW — security wrappers inherit hub timeouts). E2b#3 MED: nightly-live-smoke forcing function failing-as-documented pending autom8y#481 IAM grant — honest, but a failing-by-design nightly breeds alarm habituation if it outlives the IAM fix window. All continue-on-error sites documented [AP-07: all dimensions assessed]. |
| 6 | CI pin/version hygiene | **C** | E2b#1 HIGH: terraform-apply-reusable.yml node20 pins ×6 (checkout v4, configure-aws-credentials v4, setup-uv v4, setup-terraform v3, upload-artifact v4, app-token v1) — asana prod TF-apply chain, 06-16 deadline mid-soak. E2b#2 MED: service-terraform.yml detect-job checkout v4 skew within its own orchestration. E2b#5 LOW: test.yml reusable pin one rev behind (93dbbc29 vs f5601acb, missing --all-extras fix). Foundation otherwise strong (asana 11/12 node24-clean, satellite-dispatch DEFER documented) — that floor is why this is C, not D. |
| 7 | CI duplication | **B-** | E2b#6 LOW: CodeArtifact simple-fetch (no retry) ×3 standalone workflows vs the hardened retry pattern — inconsistent hardening for a KNOWN flake class (PR #121). E2b#7 LOW: TF_VAR env blocks ~24 vars × 2 files, drift currently ZERO but graded on divergence risk + blast radius (prod TF plan/apply) per SCAR-EA-004, not current state alone. Partial reusable adoption (hub pattern clean for security wrappers; ancillary workflows lag inline). |

**OVERALL: C** — minimum of category grades (weakest link = CI pin/version
hygiene). Never an average [AP-03].

### Severity-ranked findings (synthesis)

- **HIGH**: E2b#1 (node20 TF-apply chain, deadline 06-16 mid-soak).
- **MEDIUM**: E2b#2 (detect-job skew), E2b#3 (nightly IAM gap, tracked autom8y#481), E2b#4 (hollow .coverage diagnostic), F-1 (dead-skip file), F-2 (sprint2 epoch-tag).
- **LOW**: E2b#5, E2b#6, E2b#7, E2b#8, F-3, F-4.
- **INFO**: F-5 (1.82:1 LOC ratio, compound signal ABSENT), F-6 (focal files correctly not using _shared), F-7 (pre-saga log-call-as-oracle in test_cascade_validator.py — the exact anti-pattern the saga refuted; route to hygiene).
- **CRITICAL**: none.

### Explicit ruling on E2b#1 — bump-now vs break-at-clear

**RULING: BUMP NOW, in the autom8y monorepo, validated plan-only.** Weighing:

1. *Merging fires nothing*: terraform-apply-reusable.yml is workflow_call-only;
   a pin bump is inert until service-terraform.yml next invokes it.
2. *The chain is idle during the freeze*: deploy/TF-apply are held levers until
   06-18; a bump merged today cannot perturb the soak substrate (asana repo
   untouched; MERGE-FREEZE applies to autom8y-asana, not the monorepo, where
   β-1/#490 + β-2/#491 already merged 06-11).
3. *Waiting is the dangerous branch*: GitHub node20 brownouts begin 06-16 —
   two days BEFORE clear. An unbumped chain risks failing its FIRST post-clear
   apply exactly when the clear-day sequence needs it, converting a routine pin
   bump into an incident-time change. Bump-now inverts that: change lands in
   the idle window, brownout window opens against node24 pins.
4. *Validation without apply*: a PR touching terraform/services/** exercises the
   plan path (terraform-plan-reusable already node24-clean) — the bump is
   verifiable pre-clear with zero apply risk.

Two atomic, independently-revertible changes: (i) terraform-apply-reusable.yml
six-pin bump to the node24 SHAs already proven in terraform-plan-reusable;
(ii) service-terraform.yml detect-job checkout bump (E2b#2). NO merges from
this station — this is a directive to E4/operator routing.

### E4 directive (categories ≤ C: only #6, CI pin/version hygiene)

| Change | Spec | Surface class |
|--------|------|---------------|
| PIN-1 | terraform-apply-reusable.yml: bump 6 node20 pins → node24 SHAs (mirror terraform-plan-reusable's proven set: checkout 93cb6efe, aws-creds e7f100cf, setup-uv 08807647, upload-artifact b7c566a7, app-token bcd2ba49, setup-terraform dfe3c3f8); one commit, one file | **merge-safe-now (autom8y monorepo)** |
| PIN-2 | service-terraform.yml: detect-job checkout 34e11487→93cb6efe; one commit | **merge-safe-now (autom8y monorepo)** |
| PIN-3 | test.yml: satellite-ci-reusable pin 93dbbc29→f5601acb (picks up --all-extras consumer-gate fix); one commit | **asana-AUTHORED-HELD** (author now, hold like PR #130, merge post-clear) |
| Adjacent (B-grade, opportunistic, NOT gating) | COV-1: post-merge-coverage.yml add include-hidden-files:true (E2b#4); RETRY-1: backport CodeArtifact retry to aegis/durations-refresh/post-merge (E2b#6); TEST-1: delete-or-implement test_workspace_switching.py (F-1); TEST-2: rename sprint2 file feature-wise (F-2) | all **asana-AUTHORED-HELD** |
| Post-soak | F-3/F-4 conftest extraction at tests/integration/cache/; TF_VAR shared-block extraction (E2b#7); dockerfile-lint timeouts (E2b#8) | **post-soak** |

### Cross-rite routing

- E2b#1/#2 execution → platform/sre lane in the autom8y monorepo (eunomia does
  not merge; GUARD-EA-001).
- E2b#3 IAM grant → already tracked autom8y#481 (security/platform); watch for
  habituation if nightly stays red past the grant.
- F-7 log-call-as-oracle in test_cascade_validator.py → hygiene rite (pre-saga
  pattern, refuted by the game-day; convert to behavioral oracle).

### Entropy trend indicators

- **Lagging (current)**: C overall, driven by one time-decaying HIGH.
- **Leading, declining-risk**: 06-16 node20 deadline (time-decay — grade worsens
  by clock, not by commits); TF_VAR twin blocks (zero drift today, unguarded
  divergence seam); nightly failing-by-design (habituation risk); inline
  CodeArtifact copies lagging the hardened canonical (bespoke-accumulation
  signal, E2b §10).
- **Leading, improving**: saga focal files set the new local standard (content
  oracles, 0 xfail, transport-boundary stubs); hub-reusable adoption clean for
  all 5 security wrappers; coverage gate real at two altitudes.

### Agent-provenance analysis (structural signals only [AP-06])

Signals present: ONE epoch-tagged filename (F-2, pattern a); bespoke
step-accumulation in CI (pattern d — retry hardening added forward, never
back-propagated to 3 older inline workflows). Signals ABSENT: adversarial-file
monotonic growth (pattern b — 17 files ruled naming discipline), bespoke mock
proliferation (pattern c — index 1:1 against available shared infra). No
authorship is attributed; these are accumulation-shape observations.

---

## JOB (b) — CUSTODIAN RULING (three primitives into throughline custody)

All three registered as **CANDIDATES** — no promotions. Binding precedent
quoted from the registry (ibf §5, O-2 ruling 2026-06-11): "Gate requires 'a
SECOND satellite repo' / 'DISTINCT satellite.' ... same satellite, same
session, shared saga origin ... It does not clear the gate." Every evidence
node below is autom8y-asana — therefore NON-promoting, by rule.

### Ruling 1 — One-Gate Invariant → NEW CANDIDATE (not a §-deepening of ibf)

Registered at `.ledge/specs/THROUGHLINE-CANDIDATE-one-gate-invariant-2026-06-11.md`.
Narrow basis: ibf §1 governs TEST fidelity ("Tests guarding a production
integration boundary MUST stub ONLY the lowest client boundary..."); One-Gate
governs PRODUCTION enforcement topology ("every path of its class passes
through a single enforced primitive, proven by a content-RED at each
altitude"). Distinct falsifier (decision-logged-but-not-enforced vs
stub-theater) ⇒ distinct custody. Family bond recorded as siblings — ibf
observes the failure mode, One-Gate names the structural cure. **Honest N=1**:
the #127→#128 convergence is ONE incident; E1's two mutation-REDs (write-side
"persisted 0/3", serve-side circuit-LKG poisoned-serve) are rite-disjoint
receipts WITHIN that incident — hardening, not incrementing. Promotion gate
quoted verbatim from ibf §7 in the candidate file: "The second anchor MUST be
a DISTINCT incident at a DISTINCT satellite"; INDEX row at "N_applied >= 3
across at least two distinct incidents". [MODERATE, self-ref-capped].

### Ruling 2 — iris pipe-smoke disambiguation → CANDIDATE, technique-grade

Registered at `.ledge/specs/THROUGHLINE-CANDIDATE-iris-pipe-smoke-disambiguation-2026-06-11.md`.
**Honest N=1** (single execution, 06-11 15:40–15:56Z, same-satellite; E1's
first-party observation of the labeled 16:00Z=1302.9 burst corroborates the
SAME execution — non-incrementing). Ruled narrow as a disambiguation PRIMITIVE
consumed by the sentinel's §4, with separate custody so its counter stays
honest under reuse. The RESET arm (dark-under-200s) has never empirically
fired — recorded as design-asserted. MF-3 (stale-tree trap) carried as
registered caveat. Promotion requires a distinct-satellite anchor AND at least
one anchor exercising the RESET branch.

### Ruling 3 — soak-sentinel schema → CANDIDATE with three registered caveats

Registered at `.ledge/specs/THROUGHLINE-CANDIDATE-soak-sentinel-schema-2026-06-11.md`.
Custody covers the SCHEMA (four-receipt shape + boolean-decidable RESET-vs-LOG
law), explicitly NOT the soak verdict — the 06-18 STRONG stays clock-gated and
reserved. **Honest N=1 day executed** (sre day-1); E1's dogfood is rite-disjoint
("all four receipt sections ... execute as written by a stranger and yield
decidable rulings"; stranger-test PASS) but same-satellite, same-day —
hardening, not incrementing. MF-1 (deploy-freeze point-in-time snapshot blind
to deploy-and-revert between attestations — already bit via the #129 race),
MF-2 (gun/coherent over-deferral — first-party re-derivable, E1 proved it),
MF-3 (stale-tree trap) carried verbatim as registered caveats; adopting their
remedies is LOG-grade, touches no clock.

### Registry diff summary

- ADDED: 3 files in `.ledge/specs/` (one-gate-invariant,
  iris-pipe-smoke-disambiguation, soak-sentinel-schema), all
  `throughline_status: CANDIDATE`, all `[MODERATE, self-ref-capped]`, all N=1
  with non-incrementing corroboration explicitly fenced.
- UNCHANGED: `THROUGHLINE-integration-boundary-fidelity-2026-06-10.md` — no
  edit (no Edit primitive at this station; full-file rewrite judged
  disproportionate). Its siblings list does not yet back-link
  one-gate-invariant; the one-way sibling link lives in the new candidate file.
  DEFERRED to ibf's next custodian edit. No duplicate custody created: ibf's
  N-counters, gate text, and O-2 ruling are untouched.
- NO INDEX rows added (all three pre-threshold per index.md:62 as quoted by ibf:
  "N_applied >= 3 across at least two distinct incidents").
- NO promotions; the 06-18 STRONG seam untouched.

---

## Handoff Checklist

- [x] Grades for all 7 categories + overall (weakest-link, no averaging)
- [x] All findings carry severity with E2a/E2b evidence citations
- [x] E2b#1 bump-now ruling issued with surface class
- [x] E4 directive: atomic, independently-revertible, surface-classed
- [x] Agent-provenance: structural signals only, no authorship claims
- [x] Custody: 3 CANDIDATE registrations, honest N-counters, gate criteria quoted verbatim, no duplicate custody
- [x] Self-cap MODERATE stated in header (G-CRITIC)
- [x] No merges performed; 06-18 STRONG reserved

*Acid test: the worst category (CI pin/version hygiene, C) sets the overall;
the single highest-leverage action (PIN-1, merge-safe-now in the monorepo) is
unambiguous; cross-domain concerns are routed by name.*
