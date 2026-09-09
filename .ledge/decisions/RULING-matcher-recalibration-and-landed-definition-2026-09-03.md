---
type: decision
title: "RULING — name-matcher recalibration + landed-client definition (sitting 2026-09-03)"
date: 2026-09-03
venue: close-the-activation-loop dispatch session (operator interview via AskUserQuestion, 4 rounds, 16 questions)
status: accepted
ratification: operator selections verbatim-intent, 2026-09-03; dispatcher-authored record
discharges: G-3 (the four predicate questions) + the matcher policy fork opened by the operator on 2026-09-03
supersedes: the S-4 F-B1 strict-evidence-floor calibration (dispatcher-chosen cure (a), never operator-ratified)
related: .ledge/decisions/CHARTER-decision-space-of-record-2026-07-30.md · RULING-decision-space-amendments-2026-08-26.md · autom8y#1844 (attributed-predicate collision ruling) · .sos/wip/dre/VERDICT-close-the-activation-loop-s4.md (F-B1) · .sos/wip/WATCH-ebi-activation-train-2026-09-02.md (INITIALS routing defect)
---

# RULING — name-matcher recalibration + landed-client definition

## §0 Why this sitting

The shipped matcher (S-4, #1845, live since 2026-09-02T15:03Z) was calibrated
precision-first: a lone prefix-first candidate ("Nathan W." vs "Nathanial
Wexler") parks to a human; ties never resolve by recency; the initials-only
shape is unreachable (routing defect); full-name-no-phone is unrouted. The
operator's stated business priority is the opposite — **a missed attributable
booking is costlier than a correctable mis-attribution** — and the strict
floor was a dispatcher/critic choice (S-4 cure (a) over the recall-friendly
cure (c)), never an operator word. This sitting re-bases the policy and closes
the four open landed-client questions (G-3) that interlock with it.

## §1 Scope (R-M0)

Ratified scope = **matcher recalibration + landed-client definition**. Explicitly
NOT in this sitting: FLAG-5 (Tier-B write-back default), the nudge-outbound
classification, and the corroboration-plane rulings R1-R5 — deferred to a
later sitting by operator choice.

## §2 Matcher rulings

- **R-M1 Objective — recall-first, bounded by tier, policy varies by shape.**
  Strong evidence binds silently; weaker evidence binds as a tagged, counted,
  reversible match; thin evidence parks. (Operator: options 2 & 4 of the
  objective question.)
- **R-M2 Full-name, no phone → bind silently as HIGH** on exact full-name
  match at the office within the window. (Currently unrouted — defect.)
- **R-M3 First-name + last-initial, lone prefix-first candidate → BIND.**
  Operator verbatim intent: "if you have a clear nickname first and a last
  initial and there's only one mapped lead, then it clearly should be
  attributed appropriately." Tagged `matched_weak` as the safety net, not a
  brake. Where intake carries less certainty (no last initial, ambiguous
  nickname), **the forgiveness bar is set EMPIRICALLY** (R-M8), not by fiat.
- **R-M4 Initials-only ("N.W.") → route to the matcher (fix the gate defect)
  and bind as WEAK inside a TIGHTER window** than the 90-day default,
  reflecting the 1–2-week lead-to-booking model; the tight window's value is
  set by R-M8.
- **R-M5 Tie-break — decisive recency binds, close recency parks.** If one
  candidate is recent (order ~14 days) and the other weeks older, bind the
  recent one (tagged); if both are recent, park as ambiguous. Thresholds set
  by R-M8. This is the legacy newest-wins made loud and bounded, not removed.
- **R-M6 Reversal — manual ops re-point PLUS automatic contradiction flag.**
  Ops can re-point from the queue; the system additionally flags (never
  auto-undoes) a weak match when a later signal contradicts it (the real lead
  books separately, a phone lands on the record, a duplicate appears).
- **R-M7 Observability — NOT a gate on this recalibration.** Counted match
  outcomes (high / weak / ambiguous / organic, per shape) must be EXPOSABLE
  as a data surface; their presentation is wired into the agency view under
  active development at `~/code/a8/contente/dashboard_ui`. No CloudWatch
  dashboard/alarm work is commissioned by this ruling.
- **R-M8 Empirical calibration BEFORE landing.** Replay phone-matched
  bookings (ground truth) as if name-only, per shape and window, to measure
  real collision and mis-attribution rates; the measured rates set the
  prefix-forgiveness bar, the initials window, and the recency thresholds.
  Landing waits on this study (~1 day) and on the sibling lane's soak close
  (2026-09-04T~08:10Z) — build now, land after both.
- **R-M9 Candidate pool unchanged**: ad-attributed leads at the same office
  (path-a), 90-day default window.

## §3 Landed-client definition (discharges G-3)

- **R-L1 Which bookings count — ONLY email-forwarding-integration bookings.**
  The certificate attests this integration; other channels do not count.
- **R-L2 Test/synthetic leads — NEVER count.** Nation of Wellness (sole soak
  member on a `platform='test'` lead) is a mechanism proof, not a landed
  client, and reads 0 of 3.
- **R-L3 Weak-tier name matches — do NOT count toward certification.** They
  attribute in the product and reports; the landed certificate counts only
  phone-matched, full-name, or exact-first+initial (HIGH) bookings.
- **R-L4 Provider-dialect axis — narrow honestly to what is observed**
  (reviewwave; calendly N=1) and name janeapp/sked as unobserved. Not a hard
  ≥3 requirement; not dropped.
- **R-L5 Window — CUMULATIVE since activation.** Three clean attributed
  bookings ever, from the integration's go-live; landed stays landed. Stall
  detection is the sweeper's job, not the certificate's.
- **R-L6 "Attributed" wording** — treated as already ratified by autom8y#1844
  (collision-2 ruling). [INFERRED from the merged paper — see §5 U-3.]

## §4 The measured ground (2026-09-03, own-hands, prod, staged lookups)

- 30 clinics used email intake in 90d (42 activated per the witness census);
  1,309 bookings; 28 clinics ≥3 bookings.
- 1,291 of 1,309 match a lead by phone; **only ~55 match an AD lead**. The
  other ~1,227 match leads with no channel/platform/source — 805 of those
  leads were minted by the intake itself within ±1 min of the booking.
  **~96% of the forwarded feed is the clinic's organic calendar**; the ad-lead
  gate (#1833) now refuses those at the write, by ratified design.
- Ad-driven bookings per clinic (90d): Inver Grove 18 · Cornerstone 11 ·
  Mansour 8 · Watts 7 · Active 4 Life 3 → **5 clinics reach three in 90d,
  3 in 30d, 11 have ≥1**. Reachability of "landed" is bounded by ad-booking
  volume, not by attribution mechanics; the matcher adds the no-phone ad
  bookings on top (for JaneApp-style clinics it IS the integration).
- Consequence to expect: post-gate, email-intake booking counts fall ~96% by
  design.

## §5 Unconfirmed assumptions (carried, not ratified)

- **U-1 (A1/A7)** — mis-attribution is correctable on our side without
  clinic-visible cost. R-M6 assumes it; unverified whether a weak match
  surfaces in the clinic's own system before ops sees it.
- **U-2 (A3/A6)** — 1–2-week lead-to-booking lag and low same-office
  same-initial collision probability. Both are MEASURED by R-M8, not assumed
  past it.
- **U-3 (A10)** — that #1844 ratified the "attributed" wording. Inferred.
- **U-4** — the agency-view (dashboard_ui) will consume the counted outcomes;
  the data-surface contract between the intake and that UI is unspecified.

## §6 Deferred by the operator (explicit)

FLAG-5 write-back default · nudge-outbound classification (R-A4 floor
question; gates the re-enable) · corroboration-plane R1-R5 (six false
`diverged` stamps) · the thin-evidence forgiveness bar (→ R-M8 evidence) ·
matcher observability presentation (→ agency view).

## §7 Consequences for the wave

- S-10's predicate is now fully specified (R-L1..R-L6); the cumulative window
  makes it satisfiable for ~5 clinics today on HIGH-tier evidence.
- A recalibration sprint (S-4b) is commissioned: calibration study → routing
  fix (initials, full-name-no-phone) → tier semantics → recency tie-break →
  contradiction flag → exposable outcome counts. Disjoint critic required
  (mechanics changed under certified code). Lands after R-M8 + the sibling
  soak close; it is an EBI image event under the standing cross-lane hold
  (ping-before-merge carve-out applies as an operator-worded deploy).
