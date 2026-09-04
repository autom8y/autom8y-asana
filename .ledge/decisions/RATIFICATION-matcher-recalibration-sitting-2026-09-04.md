---
type: decision
title: "RATIFICATION — matcher-recalibration sitting (2026-09-04): release shape, G-2, G-4 seven blanks, the sentence, deferred seams"
date: 2026-09-04
venue: WAVE-2 / S-4b dispatch session (operator interview via AskUserQuestion, 4 phases, 16 questions; neutral framing; recommendations labelled)
status: accepted
ratification: operator selections verbatim-intent, 2026-09-04T18:10Z→19:05Z; dispatcher-authored record
supersedes_in_part: RULING-matcher-recalibration-and-landed-definition-2026-09-03.md (R-M6 premise → errata; "reversible when wrong" → RS-12)
governed_by: RATIFICATION-shared-front-sitting-2026-09-03.md (R-22 mechanism clause FALSIFIED 2026-09-04 — see §1; R-23/R-24/R-25/R-28 applied)
related: CHECKPOINT-matcher-recalibration-PT-02/03/04 · CONTRACT-matcher-tier-tag (rev 3) · MEASURE-matcher-arrival-rate-2026-09-03 · THREATMODEL-ebi-sender-auth-2026-09-03 · RECEIPT-R30-denominators-2026-09-04 · CARD-dead-letter-disposition-2026-09-04
---

# §0 Why this sitting
The 2026-09-03 shared-front ratification answered the reversal act (R-23) and the phone seam (R-24),
bound loosening behind the gate's tier predicate (R-25), and sequenced the thresholds behind a sender-auth
assessment (R-28) that returned the same day. PT-04 passed limb (a) at `6c44cec7` and halted limb (b) on
the operator's words. This sitting speaks them.

# §1 Pre-flight facts (own-hands, this sitting)
- Head `6c44cec7`, 2806/4/0, CI 33813320856; four PRs OPEN, automerge null; main 25 commits ahead with
  ZERO EBI source changes. Witness clock 2 of 3 (run 33843975003). Peer soak closed; peer lane DONE.
- **R-22's mechanism clause is FALSE**: the EBI lambda deploy job carries no job-level `environment:`;
  five push deploys today ran unapproved. Merge == deploy, ~12 min, all three functions.
- Shipped initials window = the 90-day pool (`activation_read_client.py:483` default). Live: 4
  matcher-reaching mails/30h, all initials, 0 qualifying. 48.66% of inbound unauthenticated by design.
- One dead-lettered booking (pk `bd875254…`), appointment slot past, 503 from the booking receiver.

# §2 Rulings
**RS-1 Release shape — EMIT-NOW, LOOSEN-LATER.** One EBI image event now: the tier is emitted and counted
on values that reproduce today's binds, plus ONE tightening (RS-6). Recall-first loosening = a second
event, after the gate's tier predicate is live (R-25) and after one read of event-one's counts (RS-14).
**RS-2 Deploy authority (G-2) — RIDE THE EXISTING GRANTS** (§2b ADMIN-GRADE + §2e click). The dispatcher
merges when the rite-disjoint certificate lands and informs after. Chosen against the veto-window
recommendation; the ungated-deploy tradeoff was disclosed and accepted. The peer pre-merge heads-up
remains a protocol act.
**RS-3 Lost booking — RE-DRIVE** (executed 18:21Z; outcome in CARD). **NEW REQUIREMENT (RETRO):**
retroactive processing of past-dated bookings after downtime/issues MUST be supported so the database
keeps accurate scheduling-performance data. Folded into the RESIDUAL-5 successor.
**RS-4 Scope — the P-3 sender-auth log line FOLDS INTO limb (b)** (one image event). The retry-exhaustion
loss floor (RESIDUAL-5) + RETRO = the FIRST successor, framed the day event one lands.
**RS-5 "Emit-now" semantics — LABEL WHAT ALREADY BINDS, TIGHTEN THE ONE FREE LEVER.** Lone prefix-first
FNLI and lone initials binds become `matched_weak` (counted; excluded from the certificate by R-L3).
**RS-6 Blank (3) INITIALS_WINDOW_DAYS = 14.** Cell C/INITIALS/14: collision [0.0, 0.0], recall
[94.7, 94.7], organic false binds 9 at 3 clinics (F-1 met at n=3, MEASURED; bracket ends coincide).
**RS-7 Blank (7) CONTRADICTION_HORIZON_DAYS = 7, PROVISIONAL.** OPERATOR-SET-ON-UNMEASURED by
construction (bind→contradiction latency unmeasured; proxy 72.2% ≤7d). Heartbeat is the instrument;
revise on evidence. Reach clause: effective_reach = min(7,7).
**RS-8 Blank (6) PLURALITY_SUPPRESSED_DISPOSITION = REFUSE.** Chosen on an empty set (1/12,660, 0
outcome changes); OPERATOR-SET-ON-UNMEASURED.
**RS-9 Blank (2) WEAK_FORGIVENESS_MIN_SCORE = STRUCK for event one.** Comparand (α/β) DEFERRED to the
loosening sitting. The trace states `below_bar` UNREACHABLE (CT-4), never zero.
**RS-10 Blank (4) R-M5 recency = NOT SET THIS WAVE** (STRIKE form). No population at 14d.
**RS-11 Blank (5) undated candidates = KEEP ELIGIBLE.** OPERATOR-SET-ON-UNMEASURED; `undated_retained`
is the instrument (DF-23).
**RS-12 The sentence — TWO-PHASE TRUTH.** "reversible when wrong" becomes **"flagged when wrong; restated
with provenance once the record-correction primitive lands"** in the RULING (errata §8), the TELOS, the
CONTRACT (rev 4, text-only), and the four PR bodies — BEFORE merge (PT-03 C12 discharged by this word).
**RS-13 Gate-predicate design (G-8) — DEFERRED to the cutover-front lane's sitting.** Their sprint, their
venue. CONSTRAINT-1 (server accepts nullable `tier` first, then client) binds regardless of design.
**RS-14 Loosening sitting — AFTER the gate predicate is live AND one read of event-one's per-shape counts.**
**RS-15 FULL_NAME and FNLI windows = 90** (today's pool; no tightening).
**RS-16 Lessons procession (discipline-extraction, consolidation mode, both classes) — AFTER event one lands.**

**Derived, recorded not asked:** Blank (1) N/A by construction (PT-02 §D). G-3 = PROPAGATE per R-24; the
seam is set to `propagate` at limb (b); D-12/D-13 dissolve (no park). G-5 dissolves (the flag is emit-only;
record correction is R3 on the dre lane). G-1 closed (not clear-to-land; RS-2 governs the merge).

# §3 Unconfirmed assumptions carried
- A8 (PT-03): today's shipped matcher binds lone prefix-first and lone initials SILENTLY as plain matches
  — inherited, not re-derived this sitting; limb (b) derives the strict-equivalent values BY RECEIPT and
  the THRESHOLD-TRACE must show that today's binds are reproduced (RS-5 is falsifiable there).
- The booking receiver behind the persistent 503 is UNIDENTIFIED (not `autom8_custom_booking_handler_prod`;
  0 invocations); first RETRO item.
- R3's resume horizon ≈ 2026-10-08 is peer-stated.
- "One read of the counts" (RS-14) presumes event one runs long enough to count something at ~3 matcher-
  reaching mails/day, all initials.
- B1 (peer): a refused weak match is "neither texted nor invoiced" — partially unverified on their side.

# §4 Deferred by the operator (explicit) — with what reopens each
Comparand α/β (→ loosening sitting) · R-M5 recency (→ loosening sitting; DF-22 if blank (3) moves to
30/45/90) · recall-first values (→ RS-14) · G-8 (→ their sitting) · procession (→ RS-16) · FLAG-5 write-back
default (still deferred from 09-03) · nudge-outbound classification (still deferred; gates the re-enable) ·
corroboration R1-R5 (their lane) · RESIDUAL-5 + RETRO (→ first successor) · DF-29..DF-36 as registered.

# §5 Teed acts
| # | Act | Seat | Gate |
|---|---|---|---|
| 1 | S-09 limb (b): sentinels → RS-6..RS-11 values; seam → propagate; P-3 log line; PT04-C4/C6/C7/C8/C9/C12/C14; THRESHOLD-TRACE; fourth truth-table derivation; §7 re-anchor | principal-engineer | qa DELTA → PT-04 delta |
| 2 | CONTRACT rev 4 (text-only): RS-12 sentence in §0; note read_failed emission fix | architect | before S-10 |
| 3 | RULING §8 errata + TELOS lines + 4 PR bodies: RS-12 wording | dispatcher (docs PR, autom8y-asana) | before merge |
| 4 | PT-04 delta on the ratified head → S-10 integrity-architect COLD | potnia → dre | first contact |
| 5 | Peer heads-up → merge under RS-2 → read-back ×3 → S-12 on G-6 | dispatcher / pipeline-steward | RS-2 |
| 6 | RESIDUAL-5 + RETRO framing | myron (/frame) | after 5 |

# §6 ADDENDUM — 2026-09-04T20:30Z, after S-09 limb (b)'s first return (two further words)

**A8 falsified by receipt** (14 constructions replayed against the shipped matcher; corroborated by
CONTRACT V-8.1's own note and RULING §0): a lone INITIALS match binds silently today (A8 TRUE on that
limb); **a lone first-name-plus-initial candidate PARKS today** (A8 FALSE on that limb). RS-5's
headline "label what already binds" therefore described only the INITIALS limb. PT-03 §I(2) carried
the wrong claim; erratum appended there. Two words spoken on the corrected premise:

**RS-17 (amends RS-9) — FNLI lone prefix-first PARKS in event one, as today.** `WEAK_FORGIVENESS_MIN_
SCORE` is SET (not struck) at the lowest achievable base score strictly above the lone prefix-first
score, derived by receipt from the head's enumeration. Comparand α/β stays DEFERRED and is MOOT this
event (recency NOT SET → bonus 0). `below_bar` becomes REACHABLE. R-M3's bind is realised at the
loosening sitting, not before (R-25).
**RS-18 — FULL_NAME exact attribution SHIPS in event one** (attribute to the existing lead at HIGH
instead of minting a new lead; R-M2; cell RM2/C wrong-bind 0/39..0/40 MEASURED at every window;
gate-neutral). Recorded as deliberate new attribution surface in S-11's landing note.
**Corrected statement of event one**: INITIALS labelled as it binds today; FNLI reproduces today's park;
the INITIALS window tightens 90→14; full-name attribution goes live; the tier is emitted and counted
on every outcome including read_failed; the P-3 sender-auth line emits. Nothing else changes.

# §7 ADDENDUM — 2026-09-04T23:00Z, after qa DELTA #2 at b7660a80 (one further word)

**RS-19 (amends RS-8) — the plurality-suppressed `refuse` disposition is SCOPED TO THE COLLIDING
CANDIDATES.** The qa seat constructed at the real stage (VERDICT §12 N2-4) that `refuse` as built is
OFFICE-WIDE for the window: `plurality_suppressed` is a pool-level flag, so one duplicate-phone lead pair
anywhere in an office's 90-day pool parked every name-evidence bind at that office — including
exact-FNLI HIGH and the FULL_NAME attribution ratified at RS-18 — as `below_bar`/`plurality_refused_*`.
Presented with that blast radius (one office today; 1/12,660 cells), the operator ruled: **only the
candidates sharing the duplicated phone are refused; unrelated candidates at the same office bind as
scored.** A mechanism change on the S-04/S-05 seam → architect seam ruling (SEAM-RULING-plurality-
scope-2026-09-04) + contract rev 6 if a clause moves + limb (b) iteration 5, BEFORE the certifier is
briefed. Companion finding recorded: the S-05 test fixture armed this seam at `bind_as_scored`, not the
ratified value, so the suite could not see the office-wide effect — the arming rule is amended to arm
the RATIFIED scoped form.
