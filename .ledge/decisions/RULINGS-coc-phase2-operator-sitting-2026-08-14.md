---
type: decision
status: accepted
id: RULINGS-coc-phase2-operator-sitting-2026-08-14
wave: chain-of-custody-closure (Phase-2 close → landing era)
date: 2026-08-14
method: "operator sitting via /consult litigation of HANDOFF-coc-phase2-close-2026-08-14 (CTO-compression: nine menu words → three clusters + one probe finding; AskUserQuestion, 4 rulings)"
self_assessment_cap: MODERATE
---

# OPERATOR RULINGS — coc Phase-2 landing era

Consumes: `HANDOFF-coc-phase2-close-2026-08-14.md` §3/§4. All words given
2026-08-14, inside the AL-5 runway (re-priced ~28h53m at 07:52Z).

## R-5 — Cluster A RULED: **FULL F-4 LIFT — land all three inside the window**

CC-5 (Tier-1 offers-warm, worktree `coc-cc5-tier1-warm` @ 6b75279f), CC-7
(gitleaks job @ a922d8f9), CC-1 (PR #365 @ 79d9f4a1) ALL proceed to
PR-up → merge-on-green-with-review → producer-deploy inside the AL-5 window
(opens ~2026-08-15T12:45Z). CC-7's branch-protection registration executes
per its RUNBOOK **only after** the job LANDS and is observed reporting (AR-1
mode-2 hazard: registered-but-unreportable blocks every merge). NEVER
`--auto` on #365 (enforce_admins); merges are manual-on-green.

**On the record**: the litigation's recommendation was the scoped lift
(CC-5-only; the clock binds only CC-5). The operator ruled FULL lift —
sovereign, accepting the compressed-review surface. The dissent is recorded,
not re-litigable at execution time.

## R-6 — Paper durability RULED: rebase + paper-PR now

The seven-commit paper lineage (464266a5→1ddfde4d, local main 7-ahead/
12-behind origin — single-machine durability, probe finding of this sitting)
is REBASED clean onto origin/main as branch `docs/coc-paper-lineage` (7/7,
tip 02ae503f before this commit) and goes up as a docs-only paper-PR,
mergeable independently. Local `main` left untouched (no reset); it
reconciles by fast-forward after the paper-PR merges.

## R-7 — Cluster B RULED: (f)+(a) remediation RATIFIED + iris card OPENED

The RE-2 remediation recommendation — **(f) in-repo `caller_service`
allowlist bridge + (a) scope-vocab durable fix** — is RATIFIED as the build
target for a security-seated wave, with a design-may-refine rider (the
Phase-2 security bench never materialized; DEV-1..4). The sharpened target
governs: **the exemption path has no filter** (one unfiltered
`if !business_scoped`; `sa_reconciler.py` re-emits the bypass tuple every
boot; 300s D5 TTL is the sole revocation bound; exempt population drifting
upward per NF-1). RE-2 severity remains **HIGH** (Critical not warranted,
per the SEC-002 trace). Iris governance-integrity finding OPENED:
`CARD-iris-scope-truth-divergence-2026-08-14.md` (this commit).

## R-8 — Cluster C RULED: peg all four, fire after A lands

- **R-CC7-1**: named follow-on triage pass (31 baseline-masked live-at-HEAD
  findings; 0 asana-native-pat) — until it runs, NO "history clean" claim may
  cite the green gate without carrying R-CC7-1.
- **FLAG-1**: `ASANA_STORY_WARM_PRIORITY_ENTITIES` is OPERATOR-RESERVED; the
  Tier-1/Tier-2 line is now configuration, not structure — pegged to the
  fleet defer-watch manifest (DW-COC-05, this sitting).
- **F-2** (cred-t21 rotation): scheduled at operator convenience; orthogonal
  (the baseline greens CI, not rotation).
- **eunomia limb-(a)**: the word auto-ripens when both WS-A halves LAND;
  re-invoke eunomia at attest time (deliberately unseated meanwhile).

## Standing state after this sitting

F-4 **LIFTED (full)** · landing era OPEN for CC-5/CC-7/CC-1 with the AL-5
clock governing · paper-PR up (this branch) · RE-2 remediation ratified
awaiting a security-seated build wave · pegs DW-COC-01..05 · CC-8 behind
CC-7's land · limb-(a) behind both WS-A halves.
