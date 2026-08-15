---
type: review
artifact_type: realization-surfacing
artifact_id: SURFACE-limb-a-live-realized-2026-08-15
status: accepted
wave: coc-arm-the-instrument
session: session-20260814-210158-d6cdff92
self_assessment_cap: MODERATE
surfaces: "limb-(a) MECHANISM-realized -> LIVE-REALIZED (SURFACED-FOR-REATTEST)"
scope_fence: "ASR report class only; live-evidenced on the abort-path subclass"
attester_of_record: "eunomia verification-auditor — OPERATOR-FIRED, not seated this wave"
---

# SURFACE — limb-(a) ripened: MECHANISM → LIVE-REALIZED, for re-attest

This record SURFACES a state change for the operator-fired eunomia re-attest. It
is not an attestation. No seat in this wave speaks the re-attest word
(`self-ref-evidence-grade-rule`; NO-CRITIC precedent of the attest wave).

## 1. The claim being surfaced

RUNG E limb (a) — machine-assembly provenance on the live delivery chain — has
moved from MECHANISM-realized (fixture-only, `VERDICT-limb-a-phase4-attest-2026-08-14.md`)
to **LIVE-REALIZED on the production wire**, scope-fenced as follows, verbatim
per the A-3 adjudication (R-1):

> live-evidenced on the abort-path subclass; readout subclass unit-proven,
> pending first readiness-pass tick.

The re-attest must NOT generalize beyond ASR's report class. `render()` (the
EX-5 item-1a readout) still has zero production callers — that §0 finding
SURVIVES this wave, named, pointed at operator-gated REC-004.

## 2. Evidence chain (each leg independently re-queryable)

- **Build**: autom8y monorepo PR #1636, squash-merge `3dde20ef`
  (2026-08-14T19:58Z). One ASR-internal canonicalization (ADR option (iv)),
  generation emission at all three assembly sites, delivery-side hash
  RE-computed in the shared `_safe_slack_post`, fail-open guard, delivered
  Slack payload pinned byte-identical by test. 679 tests green; RED-before
  captured twice as a mode-2 genuine gap (no defect injected).
  Design of record: `.ledge/decisions/DESIGN-rec002-asr-content-hash-2026-08-14.md`
  + `.ledge/decisions/ADR-asr-content-hash-canonicalization-2026-08-14.md`.
- **Deploy**: dispatch run 31835735219 — CI / Build / Deploy Lambda via
  Terraform / Smoke Advisory all success (~2026-08-14T20:05Z).
- **Live pairs** (first two post-deploy cron ticks):
  `0012255b-532f-4b86-bfa5-37b89d5bf2da` (2026-08-15T00:01Z) and
  `c047c03c-bfc0-40c2-b69d-b6c9032c2ea5` (04:01Z) — each a
  `report_generated`+`report_posted` pair with equal `content_hash`
  (`sha256:6a95314a…59be`, `sha256:eea70794…beff8`), `assembled_by=machine`,
  `human_in_loop=false` (JSON boolean), trace/span-bound, ~130ms apart.
- **A-3 adjudication (qa-adversary, own-hands re-derivation): GO.**
  L2: the actual join (`autom8_asana.observability.rung_receipts` at
  `f6dbb7b8`) over raw filter-log-events JSON → both occurrences
  `rung_e_limb_a_attestation: "observable"`, aggregate `status: "satisfied"`
  (2/2) — clause 4a genuinely attested, not the 4b block-count fallback.
  L3: input-only tamper on a scratch copy → `not_observable /
  content_hash_mismatch` while the honest pair stays observable in the same
  run; unit teeth T-2/T-3 pass verbatim in a clean worktree at `3dde20ef`
  (28/28 file-wide). L4: honest negative — zero `report_generated` and
  0/12 `content_hash` on pre-arm deliveries (2026-08-13 through
  2026-08-14T20:10Z); the arming changed the outcome, not the query.
  Receipts: A-3 adjudication artifacts (session scratchpad
  `a3-adjudication/`), UTC 05:13–05:17Z 2026-08-15.

Live join occurrence count moved **0 → 2** against the attest wave's §0
baseline (57 receipts / 0 hashed / 0 pairs ever).

## 3. UV-P discharges and residuals carried

- Discharged by live receipt (UV-P RULE-1): UV-A-1 (the attest wave's
  "observe_limb_a over live corpus derived, not executed") — L2 executed it
  over live production events; and A-2's own deferred-to-post-deploy UV-P.
- `schema.py` docstrings stating the generation query "returns zero rows
  until EX-5 ships" are now stale in the good direction (R-7) — code-comment
  refresh is a named follow-on, not done here.
- Full residual set R-1..R-10 in the A-3 adjudication, of which the
  load-bearing three: **R-2** armed-as-emitter (mismatch fires only when the
  join runs; continuous detection/paging is a follow-on sre lane), **R-3**
  hash-absence regression returns swap-blindness with no tripwire (proposed
  watch: hashed-vs-total `report_posted` deadman), **R-4** ingestion must
  remain raw JSON (`bool("false")` string-coercion misclassifies; the
  `GENERATION_LOGS_INSIGHTS_QUERY` constant used naively reproduces it —
  fail-closed direction, wrong reason).

## 4. What the re-attest word would flip

`.know/telos/chain-of-custody-closure.md` limb-(a) line, and the CC-8 item
(ii) un-flag write-back (ruled to eunomia at its next touch by
`RULING-cc8-item2-owner-2026-08-14.md:18`, still without a completion
receipt). Both are eunomia's to record, operator-fired, in one touch.

Evidence grade: MODERATE (self-referential ceiling). Every mechanical receipt
above is independently re-queryable by run id, commit sha, or log query.
