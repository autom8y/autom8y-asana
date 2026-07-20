---
type: decision
artifact: operator-rulings-record
initiative: asana-mcp (v1 + postfelt-hardening + second-leg horizon)
date: 2026-07-20
method: >-
  Structured operator interview (/interview, AskUserQuestion), four adaptive
  phases (orientation → constraints → pillar litigation with adversarial cases
  presented first → convergence). Every ruling below was confirmed by the
  operator at Phase 4 ("Confirm as drafted" on all four blocks, zero amendments,
  zero strikes). Selections quoted verbatim where the operator chose a labeled
  option; free-text answers quoted verbatim.
operator: Tom Tenuta
scribed_by: dispatcher session b3f74f84 (scribe-at-direction; content is the operator's)
evidence_ceiling: the rulings ARE operator primary source; scribing self-caps MODERATE
---

# OPERATOR RULINGS — telos-level ratification of the open decision space (2026-07-20)

## Block I — Identity & value bar

**R1 · Identity — RATIFIED.** The AI-assistant integration is ALL FOUR at once —
"Daily working tool, Proving ground, Foundation piece, Operator power tool"
(verbatim multi-select). No single identity is imposed; downstream rulings must
preserve this optionality.
*Unblocks*: framing of all future proposals (no forced pivot to a single purpose).

**R2 · Value bar — RATIFIED.** "Worth it" at review time = "New capability proven" +
"Nothing bad happened" (verbatim selections). Deliberately NOT usage counts,
deliberately NOT time-saved metrics — the bar is the capability ceiling plus a
clean safety record.
*Unblocks*: evidence collection priorities for the review window; how the second
integration's success will be judged.

**R3 · Attention — RATIFIED.** Operator verbatim: "1&2 resonate" — a blend of
front-burner (active daily use, push adoption, fix friction fast) and steady
simmer (use where natural, fix what genuinely blocks).
*Unblocks*: pacing decisions for every open exploration.

## Block II — Guardrails & delegations

**R4 · Yours-only powers — RATIFIED.** Three powers require the operator's hand,
indefinitely: "Who can use it" (any exposure beyond the internal team),
"Production changes" (infrastructure serving real traffic), "Goal & record
sign-offs" (verbatim selections). NOTE: "New action types" was deliberately NOT
retained in this set — see R7 for its replacement rule.

**R5 · Confirmation rule — AMENDED (standing posture changes).** Human
confirmation is required before "Automation triggers only" (verbatim): actions
known to set off business automations (today: applying a routing label) pause
for a human yes; plain saves and completes flow freely. This is STRICTER than
the built behavior (act-with-warning + verify-after) →
**BUILD ITEM RB-1 (new work)**: a confirm-before-firing gate on
automation-triggering writes in the assistant surface, with the
trigger-classification list as its maintained boundary.

**R6 · Delegations extended — RATIFIED.** All three offered delegations granted
(verbatim multi-select): "Team uses writes solo" (within R5), "Read-only growth
is free" (new questions/lookups need no pre-approval; writes stay frozen),
"Reliability tuning is free" (within already-accepted safety bounds; operator
reads about it in records rather than approving live).

**R7 · New-actions rule — AMENDED (replaces ask-me-every-time).** "Reviewed +
guarded = go" (verbatim): new action types may ship after independent review,
provided any automation-triggering one arrives with the R5 confirm-before-firing
guardrail built in from day one. The operator learns of new actions from the
record, not by pre-approving each.
*Unblocks*: the deferred label-creation verb (and any future verb) now travels
the review+guardrail path instead of waiting on an operator ruling; the
charter's original per-verb operator freeze is superseded BY THE OPERATOR'S OWN
HAND for verb additions (write verbs remain governed — by review + guardrail,
not by per-item operator approval). Exposure and production powers (R4)
unaffected.

## Block III — Instruments

**R8 · Goal document — RATIFIED (signed as-written).** "Sign as-written"
(verbatim): the postfelt-hardening telos binds with its verification deadline
2026-08-14 and its named rite-disjoint attester unamended. The operator
knowingly accepted the decision-before-review date order — rendered moot by
R11's early ruling.
*Executed in this PR*: telos status PROPOSED → RATIFIED with this record as
receipt.

**R9 · Retry label — AMENDED (annotation flips).** "Flip to safe-to-retry"
(verbatim): tasks.py's update-task route annotation flips
`idempotent: False → True` on the probe evidence (C2 receipt, dossier A1.2:
re-running the save was side-effect-silent under a live Rules listener; the
double-fire mechanism was tag re-application, not the re-PUT — dossier A1.3).
Deliberately WITHOUT the future-binding automation-design rule (the "Flip +
bind future builds" option was offered and not chosen): the promise rests on
evidence, not a policed constraint.
*Executed in this PR*: the code flip + docstring re-scope per fork (a)'s own
spec; dossier §A1.4 marked at the operator's direction. This completes
predicate limb (c) of the hardening effort to RECONCILED — a future re-attest
may lift the telos token accordingly (the PT-09 verdict's pathway).

**R10 · Warm-up — RATIFIED (mandate, not watch).** "Plan the fix soon"
(verbatim): a faster-startup proposal is mandated in the coming weeks, budgeted
and prioritized against other work — superseding the passive watch posture of
defer-watch entry 17 (the entry stays as the evidence anchor; its disposition
is now MANDATED-PROPOSAL). **WORK ITEM RB-2**: the faster-startup proposal.

## Block IV — Horizon

**R11 · Expansion — RATIFIED: COMMIT, ruled early.** "Commit now" (verbatim):
the second AI-assistant integration — same approach, pointed at the data
service — is green-lit 2026-07-20, fourteen days ahead of its scheduled
2026-08-03 decision date, by the operator's hand with the adversarial case
presented and on the record. Effects per the standing decision framework: the
D1–D11 evaluation slate becomes mandatory-to-evaluate; the
reference-then-promote path opens. **WORK ITEM RB-3**: scoping proposal for the
second integration (who/when/budget deliberately undecided — see below).
*Executed in this PR's sibling edit*: the probe entry inscribed
Ruling: COMMIT, dated, operator-attributed.

**R12 · Exploration set — EXPLORE ×4.** Opened for active investigation and
proposals (verbatim multi-select): "Team daily workflows",
"Trigger-confirmation loop", "Cross-service answers", "Richer context
surfaces". Opening means proposals may be brought; nothing ships outside the
normal gates. External exposure was NOT opened (R4 keeps it operator-only).

## Deliberately left undecided (named so silence is never consent)

1. **Save-triggered automation design constraint** — R9 flipped the label
   WITHOUT binding future automations to re-run tolerance; anyone building a
   save-triggered automation later re-opens this question then.
2. **Second-integration scoping** (who builds, when, budget) — R11 commits the
   direction; the scoping proposal (RB-3) will carry real numbers for separate
   approval under R4's production power.
3. **Trigger-classification ownership** — R5 and R7 both depend on the list of
   which actions/labels trigger automations; who maintains that list is
   unassigned (falls to the RB-1 proposal to answer).
4. **External exposure** — closed under R4, not deferred: it reopens only by
   the operator raising it.
5. **The review auditor's identity** — signed as-written in R8; unexamined
   beyond that signature by design.

## Questions deliberately NOT asked (and why)

1. **"Should exploration of external/client exposure be opened?"** — Phase 2
   placed who-can-use-it in the yours-only set; asking would have invited
   drift against a constraint the operator had just set. It stays closed until
   the operator raises it.
2. **The action-chain library direction** (from the north-star map) — its
   governance question was consumed by R7 (reviewed + guarded = go); asking
   separately would have re-litigated a rule already given.
3. **Stale working-copy sync and duplicate routed-task cleanup** — mechanical
   housekeeping with a written recipe, not decisions; they remain on the
   operator's list untouched by this record.
4. **Who/when/budget for the second integration** — asking now would extract
   guesses; the scoping proposal will surface real numbers for a real approval.
5. **Whether to re-run the formal attestation after limb (c) completes** — a
   process question the record's own pathway already answers (a re-attest MAY
   lift the token; nothing obliges one on a date); asking would manufacture a
   deadline the operator did not set.

## Work queue minted by this record (for future sessions; none started here)

- **RB-1**: confirm-before-firing gate on automation-triggering writes (R5).
- **RB-2**: faster-startup proposal, budgeted (R10).
- **RB-3**: second-integration scoping proposal (R11).
- **RB-4..7**: the four opened explorations (R12) — proposals welcome under R3
  pacing.
