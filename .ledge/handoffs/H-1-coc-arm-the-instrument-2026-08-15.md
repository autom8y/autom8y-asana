---
type: handoff
artifact_type: wave-close-handoff
artifact_id: H-1-coc-arm-the-instrument-2026-08-15
status: accepted
wave: coc-arm-the-instrument
session: session-20260814-210158-d6cdff92
rite: 10x-dev (sre + eunomia co-seated)
self_assessment_cap: MODERATE
charge_ref: "operator ruling 2026-08-14 — CURE-1 arm the swap detector (Phase-3/REC-002), CURE-2 retire fleet || true at locus (a)"
law_refs:
  - .ledge/handoffs/HANDOFF-coc-attest-close-2026-08-14.md (H-6 §0+§7)
  - .ledge/reviews/VERDICT-limb-a-phase4-attest-2026-08-14.md
  - .ledge/decisions/RULING-cc8-item2-owner-2026-08-14.md
---

# H-1 — coc-arm-the-instrument: both cures merged+deployed+proven; limb-(a) surfaced for re-attest

## 0. Outcome in one paragraph

The attest wave's §0 LOUD finding is cured on the wire. CURE-1: the production
ASR delivery path now emits a `report_generated`+`report_posted` pair with a
recomputed, matching `content_hash` on every tick (autom8y PR #1636 →
`3dde20ef`, auto-deployed 2026-08-14T20:05Z); the first two live ticks
traversed the join's OBSERVABLE branch — live join occurrence count moved
**0 → 2** — and qa-adversary adjudicated the two-sided proof **GO**
(`SURFACE-limb-a-live-realized-2026-08-15.md`). CURE-2: the fleet `|| true`
at locus (a) is retired at source (autom8y-workflows PR #30 → `6753f943`)
with a two-sided canary showing the un-swallowed gate biting and the old
swallow actively masking an identical finding set
(`DISCHARGE-dw-coc-03-locus-a-2026-08-14.md`). Limb-(a) is SURFACED as
LIVE-REALIZED (scope-fenced) for the operator-fired eunomia re-attest; no
seat in this wave spoke a re-attest word.

## 1. CURE-1 receipts (arm the instrument)

- Design + ADR: `DESIGN-rec002-asr-content-hash-2026-08-14.md`,
  `ADR-asr-content-hash-canonicalization-2026-08-14.md` (option (iv)
  ASR-internal single function; (iv)→(iii) migration trip-wire = first
  EX-5-rendered payload entering ASR egress, i.e. REC-004).
- Build: PR #1636 (base == origin/main `a56e7896`), squash `3dde20ef`;
  679 tests pass; RED-before ×2 as mode-2 genuine gap; delivered payload
  byte-identical by test; all three `_safe_slack_post` call sites covered —
  which is why the abort-path ticks emitted at all.
- Deploy: dispatch run 31835735219, all stages success.
- Live: pairs `0012255b…` (00:01Z) and `c047c03c…` (04:01Z), equal hashes,
  `assembled_by=machine`, `human_in_loop=false`; zero `slack_post_failed`.
- Adjudication: A-3 GO — join over raw live JSON → `satisfied` 2/2; tamper
  (input-only, scratch copy) → `content_hash_mismatch`; honest-negative
  0/12 pre-arm. Full receipts + R-1..R-10 residuals in the A-3 record
  (session scratchpad) and the SURFACE record.
- Grant note (charter §7, surfaced not silent): this wave implemented
  REC-002 **conjunct (b) only** (additive log emissions) under the
  operator's explicit Phase-3/REC-002 charge; conjunct (a) — wiring the
  EX-5 readout into ASR egress, i.e. changing what humans receive —
  remains OPERATOR-RESERVED with REC-004.

## 2. CURE-2 receipts (locus (a) retirement)

- Canary evidence cited (charge requirement): `VERDICT-cc8-partial-attest-2026-08-14.md`
  §5.4 — enforcing leg FAILURE vs delegated leg SUCCESS on the same
  secret-bearing head.
- Cure: autom8y-workflows PR #30 → `6753f943`; one-line swallow removal;
  baseline-path input REJECTED as unnecessary (gitleaks auto-discovers
  repo-root `.gitleaksignore` — `cmd/root.go:249/:255/:261`, corroborated
  by SARIF `results_count: 0` at asana HEAD).
- Proof: B-2 three-arm receipts — RED run 31834106067 (FAILURE,
  `leaks found: 2`), HONEST-NEGATIVE run 31834109249 (SUCCESS on the
  byte-identical finding set under the restored swallow), GREEN runs
  31833523709 / 31833724353. Single-variable causation; canaries retired
  unmerged, branches deleted, zero alerts remaining.
- DW-COC-03 discharge recorded: `DISCHARGE-dw-coc-03-locus-a-2026-08-14.md`.
- Rider fix: PR #377 → `f6dbb7b8` corrected the inverted retirement-order
  comment (de-register FIRST, then delete — the prior order froze all
  merges with no bypass under `enforce_admins: true`).

## 3. Operator levers (each needs an owner's word; none acted on this wave)

| # | Lever | State staged by this wave |
|---|---|---|
| 1 | **Eunomia re-attest** of limb-(a) (+ CC-8 item (ii) un-flag write-back in the same touch, per RULING-cc8-item2-owner:18) | SURFACE record ripened; scope fence R-1 verbatim inside it |
| 2 | **Consumer re-pin ladder** (9 external repos, all SHA-pinned, inert) | asana re-pin evidence: would arm GREEN (auto-discovered 49-entry baseline; R-CC7-1 fence applies — gate proves "no unbaselined finding", never "history clean"). 8 private consumers have NO baseline (4 no config) — enumerate per-repo before re-pin; honest RED is possible there and is the point. Monorepo re-pin = two-file change (`gitleaks.yml:13` + `required-contexts.expected.txt:34`) |
| 3 | **Enforcing-fork retirement** | De-register `Secrets Scan (enforcing)` FIRST (repo-admin), THEN delete `gitleaks-enforcing.yml` — order now correct on the record (#377) |
| 4 | **F-2 cred-t21 rotation** | Untouched; "history clean" language stays FORBIDDEN until it lands |
| 5 | **REC-004** (live EX-5 readout discharge; gives `render()` its production caller) | Untouched, credential-bearing, operator-only; ladder position after REC-002 per the ordering law |
| 6 | **R-2 follow-on sre lane**: continuous swap detection (run the join on a schedule + page on `content_hash_mismatch`) | Proposed; today mismatch fires only when an attester runs the join |
| 7 | **R-3 watch**: hash-presence deadman (hashed vs total `report_posted`/day) — a hashless regression silently returns swap-blindness via the 4b fallback | Proposed |
| 8 | **ADR trip-wire owner-of-record** ((iv)→(iii) migration) | PROPOSED in the ADR (autom8y-asana 10x-dev architect seat); needs ratification — until then recorded-and-unwatched |
| 9 | **image_tag pin refresh** (`terraform/services/account-status-recon/production.tfvars:30`) | HAZARD H-2 standing: any manual apply there can roll the Lambda back past `3dde20ef` and silently un-arm the instrument while the paper reads LIVE-REALIZED |

## 4. UV-P ledger delta

- Discharged by live receipt: UV-A-1 (join over live corpus now EXECUTED,
  2/2); A-2's deferred-to-post-deploy live-traversal UV-P.
- Standing (inherited, unchanged): UV-A-3 admin-PATCH bypass (accepted
  permanent), UV-B-1/2/3 (CI-side gitleaks reproductions), UV-CoC-2
  (verification_deadline stays PROPOSED).
- New: readout-subclass live observation pending first readiness-pass tick
  (R-1); per-repo RED/GREEN state of the 8 private consumers under a biting
  gate (B-0 Q6, method: per-repo scan, deferred).

## 5. Stop-line receipt (standing law, adopted 2026-08-14)

The wave's paper corpus = the five artifacts of this wave
(DESIGN, ADR, DISCHARGE, SURFACE, this H-1). Close is claimable only after
the paper commit is pushed and merged on origin/main and `git status` shows
zero untracked `.ledge`/`.know` artifacts of this wave — the verification is
performed at close on the main thread and its receipt (merge sha + clean
status excerpt) is recorded in the session log. "Paper authored" does not
suffice; this section exists so the reader can check the claim against
origin, not against this file's presence in a working tree.

Evidence grade: MODERATE throughout (self-referential ceiling); mechanical
receipts are independently re-queryable by PR number, run id, commit sha,
and CloudWatch query.
