---
type: decision
status: proposed
artifact_id: PACKET-option4-interview-stack-2026-08-12
initiative: option4-verification-axis-gate (OPENED by RULING-operator-wave-close-realized-mechanism-2026-08-12)
crusade_of_origin: offers-freshness-axis-contract
session: session-20260811-115247-a1ccd942
date: 2026-08-12
purpose: >-
  The staged decision stack for the next operator /interview sitting. NOTHING
  in this packet is decided. Per the operator's inscribed interview discipline:
  one decision per question · plain language · neutral framing with the
  recommendation revealed only AFTER the answer · falsification questions on
  load-bearing commitments · HOLD is first-class · read-backs after each
  answer · written ruling record (RATIFIED/AMENDED/REFUSED/HOLD) inscribed to
  .ledge/decisions/. "Nothing I don't explicitly rule on may be recorded as
  decided."
evidence_bundle:
  - .sos/wip/SPIKE-offers-gate-direction-adjudication-2026-08-12.md  # incl. 4 correction banners
  - .sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md           # the 29-day measurement
  - .ledge/reviews/ATTEST-rel6-realize-offers-content-axis-2026-08-12.md
  - .sos/wip/CONSULT-pythia-d5b-routing-2026-08-12.md                # routing ruling + P-1..P-9
  - .ledge/decisions/ADR-006-freshness-equals-verification-recency.md # status: proposed-revised
  - .sos/wip/CONTRACT-offers-freshness-axis-frozen-2026-08-11.md     # §1.2 :150, §1.4 :262
annex: .sos/wip/DESIGN-option4-verification-axis-annex-2026-08-12.md  # DELIVERED 2026-08-12 ~08:20Z — 12 sections, 8 recommendations, V=14400 headline (derived abort = the consumer contract's own 8h), 5 premise-corrections incl. B3 split (name-join blocks ADR-006's CLI only, NOT Option 4)
annex_falsifiers:
  - "§10.4 UV-P CLOSED 2026-08-12 08:2xZ (main thread, source_coverage_deadman.tf read): the source-coverage deadman does NOT re-weigh Option 5. It keys on SourceCoverage3of3, which zeroes on aborted runs (join suppressed) — it catches abort-streaks as a side effect — but in the Option-5 frozen-frame case the join RUNS with full completeness, coverage reads 3-of-3 present, alarm stays OK. Option 5's flaw stands; Option 4 unchallenged. BONUS for C3/P-9: the file header names the success-deadman as count-gated via schedules_enabled with the 'detector dies with the schedule' (AI-6) hazard, and records billing dark since 2026-07-31 — both leads for the sre determination."
  - "§1.3 UV-P CLOSED 2026-08-12 ~08:50Z → .sos/wip/EVIDENCE-age-at-tick-v-sizing-2026-08-12.md (126 organic ticks/29d, own-trace confound removed). VERDICT: V=14400 HOLDS — 100% PASS and 100% not-ABORT on both series (verification-stamp median 3408s/max 13071s; frame-build median 6229s/max 14324s); age>28800 occurs ZERO times in 42,241 continuous minute-samples; weekend is STRONGER not weaker (45/45 vs the content axis's 0/24); tail causes all platform-engineerable (4h warm ceiling, overnight request drought, one stack-traced build failure). TWO CORRECTIONS RIDE WITH RATIFICATION: (1) the annex's inter-build-max ground was a 15-day artefact — nine 30d gaps exceed 14400 and V passes on 76s of margin at the observed max; the load-bearing line is the ABORT line (1.72-2.20x everywhere), size confidence there; (2) ⚠ THE DOMINANT OPEN DETERMINANT IS B3-a stamp-eligibility, not cadence: 18-19 of 34 sections sat unstamped 6.7 days (closed by FIX-1 #299 at 5d62d0b8; ~19 classification-scoped sections are zero-row); if the built gate's min(last_verified_at) includes zero-row sections that window reads 0/37 at 21x the abort line while every frame-level figure reads 100%. B3-a decides which of those two numbers is the gate."
---

# INTERVIEW STACK — Option 4: the verification-axis gate

**The forcing fact (W-1, 29 days, 175 ticks):** no content-age threshold both
passes healthy-quiet ticks and detects a stuck pipeline. 95 % not-ABORT demands
a 47.6 h abort line vs an 8 h consumer contract. Deployed 3600 s passed 0/175.
The inter-cohort spread is a 1 s/s sawtooth peaking Monday mornings (median
10.6 h, max 88.3 h). **Option 1 is measurement-dead; Option 4 is the only path
reconciling the two goals.**

## Block A — Governance (operator-personal, pythia consult §4-§5)

**A1 · §1.2 advancement-law amendment.** May VERIFICATION-RECENCY become an
axis that advances freshness for the offers gate? Today §1.2 (frozen, RATIFIED)
permits only CONTENT to advance. Process per precedent [A-2026-08-03]:
interview → amendment inscribed IN PLACE (superseded text left standing) → PR.
⚠ Pythia's named non-escape: a "refusal-only conjunct" framing that textually
preserves §1.2 is operationally useless (the problem is too MANY refusals) —
the amendment must let verification recency REPLACE content age as the
advancing quantity, or be refused honestly.
*Falsification question to ask:* what evidence would show verification recency
is the WRONG gate quantity for a full-state join? (Candidate: a case where a
verified-complete-but-old snapshot produced a materially wrong verdict.)

**A2 · ADR-006 disposition.** `status: proposed-revised` since 2026-05-27 with
SHIPPED, live, load-bearing code (`last_verified_at`,
`compute_verification_age`). Accept / supersede-into-Option-4's-ADR / retire.
Leaving it in limbo was pythia P-1's named governance debt.

**A3 · D-5b retirement.** The threshold question W-1 mooted: no number works,
and partition-sensitivity showed 29.8–70.8 h even under adversarial cohort
re-partitions. Retire D-5b as evidence-closed, or re-scope it (e.g.
per-cohort tolerances — pythia: that is a policy choice, not an aggregation
fix). The F-GUARD 60 s provisional allowance and HELD-2 are BOUND to this card
(S5 handoff §3-#5) and need explicit carry-or-close.

**A4 · Interim posture (Option 3 made explicit, time-boxed).** Until Option 4
lands: ASR offers ticks abort honestly at unmoved 3600 s. The readout stays
dark; per-tick verdict history is irrecoverably lost; the consumer's 8 h
tolerance stays breached. Rule it AS the interim posture with a named review
horizon — or direct an interim mitigation. (L4 keep-warm remains REFUSED unless
explicitly un-refused here; note the control-arm rationale expired with the
wave close.)

## Block B — Option-4 preconditions (each needs a ruling before build)

**B1 · §1.4 co-sourcing-compliant capture.** `compute_verification_age` reads
the S3 manifest LIVE while bytes serve from the cache tier — the exact shape
§1.4 forbids. The honest design captures verification recency INTO the frame at
build time (signal = pure function of served bytes; the Lane-G argument).
Producer engineering. Ratify direction; architect annex carries the shape.

**B2 · `backfill_used` refusal semantics.** The producer falls back to
`written_at` (MUTATION-recency) when `last_verified_at is None` — the same
false-stale generator one layer up. Rule: the gate must refuse-or-disclose on
backfilled stamps (which disposition?).

**B3 · Name-join re-seed verification.** `compute_verification_age` joins on
`SectionInfo.name`, recorded null on 100 % of prod sections at ADR-006 QA time;
null-name entries are silently skipped → `VerificationAge.unavailable`. An
unverified precondition under the whole design. Rule the verification method
and its owner.

**B4 · DEFECT-1 + DEFECT-2 as Option-4 blockers or parallel work.**
W-1 surfaced: (1) concurrent divergent section manifests (watermarks
alternating probe-to-probe for 29 days; replica non-determinism); (2) a 70.9-day
BACKWARD watermark jump on an activating section (did not bind only because
`max()` shielded it — the verification axis will read these same manifests).
Rule: fix-before-build, build-with-guards, or parallel-track.

## Block C — Authorizations (fleet-executable once ruled)

**C1 · W-4 per-constituent disclosure patch.** Additive logging on the silent
clean-GATE path (constituent name, age, watermark, which binds). Zero
gate-outcome delta, proven two-sided. Pythia: correct, not the gate; merge
with-or-after the threshold disposition. Authorize authoring+merge?

**C2 · AL-5 correction (two-stage).** (i) Description fix: it asserts "fires
iff an ASR tick would abort" — falsified in both directions since the cure
(its input read 6581/6619/6584 s at the three aborting ticks). Author-then-
apply, plan shown first (live-alarm terraform scar). (ii) Re-point decision:
what SHOULD AL-5 predict now, and book its re-baseline — FIX-N-C1 (merging
09:20Z today) changes its input quantity from ~0-anchored to true substrate
age (pythia P-8): no AL-5 reading is comparable across that boundary.

**C3 · success-deadman determination (P-9).** OK-for-9-days through 9 aborts
under treat_missing_data=breaching — either count-gated out or expression-
rescued; ten minutes of sre work. Plus the single-stray-publish rescue smell on
completion-event windows. Route to sre (borrow not currently seated at this
repo — `ari rite invoke sre`)?

## Protocol note for the sitting

Recommended order: A4 first (the live-cost item), then A1 (everything hangs on
it), then B1-B4, then A2/A3 cleanup, then C1-C3 authorizations. If A1 is
REFUSED, blocks B and C1 collapse and the sitting reduces to A4's posture +
C2/C3 hygiene. HOLD on A1 = the interim posture must get a review date.
