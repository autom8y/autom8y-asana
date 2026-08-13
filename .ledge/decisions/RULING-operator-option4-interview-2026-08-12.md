---
type: decision
status: accepted
artifact_id: RULING-operator-option4-interview-2026-08-12
initiative: option4-verification-axis-gate (opened by RULING-operator-wave-close-realized-mechanism-2026-08-12)
session: session-20260811-115247-a1ccd942
date: 2026-08-12
conducted: "2026-08-12 ~10:30-11:05Z, three AskUserQuestion batches (12 decisions), per the operator's inscribed interview protocol: one decision/question, neutral stems with assumptions stated, recommendations revealed only post-answer, read-backs, HOLD first-class"
evidence_base: PACKET-option4-interview-stack-2026-08-12.md + DESIGN-option4-verification-axis-annex + EVIDENCE-w1-cohort-spread-14day + EVIDENCE-age-at-tick-v-sizing + DETERMINATION-w2-deadmen-al5 + CONSULT-pythia-d5b-routing
binding_note: "Nothing not explicitly ruled here may be recorded as decided."
---

# OPERATOR RATIFICATION DIGEST — Option-4 interview sitting

## Rulings (12)

| # | Decision | Ruling | Operator's answer (verbatim option) |
|---|---|---|---|
| P-1 | Gate quantity | **RATIFIED** | "Both, disclosed separately" — gate on verification recency; content age rides the wire as first-class disclosure, never conflated. **Entails the §1.2 advancement-law amendment** (assumption (iv) was on the table when chosen). |
| P-2 | Build appetite | **RATIFIED** | "Full chain, one initiative" — producer capture → SDK → consumer, K-lane sequenced, B-block preconditions gated inside. |
| P-3 | Interim posture | **RATIFIED** | "Accept until replaced" — honest aborts continue with NO clock; the successor's landing is the only exit. *(Diverged from recommendation [time-boxed]; recorded as ruled.)* |
| P-4 | "Done" bar | **RATIFIED** | "Observability truthful first" — stage 1: every alarm/description tells the truth; stage 2: gate closes under the statistical bar (≥95% healthy-pass / ≤8h detection over a soak window). |
| P-5 | min() scope | **RATIFIED** | "All classified sections" — verified-empty is still verified; zero-row sections must be stamped and included. **Consequence (binding): the stamp-eligibility producer fix is a HARD PRECONDITION of gate-live** (else permanent 0%). |
| P-6 | Backfill semantics | **RATIFIED** | "Close at source, then refuse" — fetch-completion stamps verification honestly; thereafter unstamped = unknown = refuse (annex option iv). |
| P-7 | Stage-1 authorizations | **RATIFIED (all four)** | (a) AL-5 two-place description fix — plan shown before apply; (b) AL-5 flapping mitigation — authored, shown before apply; (c) latency-truth corrections (~18h reality replaces every ~12h claim) + P9-FIX-4; (d) stray-publish fix routed monorepo-side with W-2 receipts. |
| P-8 | ADR-006 | **RATIFIED** | "Supersede into new ADR" — one principle covering both surfaces (metrics CLI + query wire); ADR-006 marked superseded-by at new-ADR draft. |
| P-9 | Falsification register | **RATIFIED (3 kill-switches)** | Registered: (1) wrong-verdict case — a verified-complete-and-recent snapshot produces a materially wrong published verdict traceable to data age; (2) stamp-integrity failure — verification errs FRESH against demonstrable Asana truth; (3) soak bar missed — 14-day soak fails ≥95%/≤8h. Any seat observing one HALTS and escalates, never argues. **"Eligibility unfixable" was explicitly NOT registered** — operator treats it as a redesign trigger for P-5, not a pillar kill. *(Diverged from recommendation [all four]; recorded as ruled.)* |
| P-10 | D-5b (content threshold afterlife) | **HOLD (parked)** | "Park, revisit post-landing" — the threshold's afterlife is unruled until the verification gate is LIVE. **Revisit trigger: gate-live.** *(Diverged from recommendation [retire; keep 3600 as anomaly line].)* |
| P-11 | DEFECT-1/2 | **RATIFIED** | "G-1 in design; defects parallel" — the gate ships with the monotone-envelope guard absorbing regression events (min() is attracted to them where max() shielded); DEFECT-1 (ETag-less manifest RMW) and DEFECT-2 (70.9-day backward jump) root-cause fixes proceed as parallel producer work, not blockers. |
| P-12 | Naming fence | **RATIFIED as proposed** | `content_age_seconds` keeps its exact current meaning forever (result-scoped content age); the new axis ships as `verification_age_seconds` + `verified_at` + `backfill_used`; NO field ever polymorphic; NO consumer coalescing ("whichever is present" is forbidden). Non-aliasing clause extends to the verification family. **HELD-2 CLOSES.** |

## Explicitly deferred
- **D-5b afterlife** (P-10) — parked, trigger = gate-live.

## Assumptions remaining UNCONFIRMED (not decided today)
1. **V = 14,400s itself was NOT ratified** — the annex proposes it and the
   age-at-tick evidence supports it (100% pass, abort line = the consumer's own
   8h), but the number goes to ratification at the new ADR's draft, alongside
   the evidence's two riders (size confidence on the ABORT line, not V — 76s
   margin at the observed max; and the 30-day inter-build tail).
2. **The §1.2 amendment TEXT** — direction ratified (P-1); the in-place
   amendment wording is drafted in the new ADR and ratified there, per the
   [A-2026-08-03] precedent (superseded text left standing).
3. **F-GUARD 60s future-skew allowance** — formally bound to the parked D-5b
   card; carries with the park, unresolved.
4. **Stage-1 (a)/(b) applies are contingent on plan review** — authorization
   granted, execution waits on the shown plan.

## Interview protocol notes
- Recommendations were revealed only after each answer. Alignments: P-1, P-2,
  P-4, P-5 (with the sequencing consequence made explicit), P-6, P-7, P-8,
  P-11, P-12. Divergences (stated once, not re-argued): P-3, P-9, P-10.
- The naming-fence stem carried a flagged escape ("simplify to one number")
  that would have amended P-1; not taken.
