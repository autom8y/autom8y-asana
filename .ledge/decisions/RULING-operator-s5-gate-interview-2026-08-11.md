---
type: decision
status: accepted
artifact_id: RULING-operator-s5-gate-interview-2026-08-11
crusade: offers-freshness-axis-contract (renamed this ruling; formerly offers-false-staleness-cure)
session: session-20260811-115247-a1ccd942
date: 2026-08-11
method: structured operator interview (/interview) — one decision per question, neutral framing, recommendation disclosed only post-answer, read-back confirmed per ruling, HOLD first-class
source_handoff: .ledge/handoffs/HANDOFF-offers-cure-to-operator-s5-gate-2026-08-11.md
---

# OPERATOR RULINGS — S5 gate ratification interview, 2026-08-11

Every ruling below was answered, disclosed against the record's recommendation,
and read-back-confirmed by the operator. Nothing not explicitly ruled is
recorded as decided.

## R-1 · Cure approach — **RATIFIED**
Verbatim: "Stand by the new check" → confirmed post-disclosure.
The reconciliation gate judges freshness by the newest edit timestamp in the
rows it receives (result-scoped content axis, Lane K), with all five
loud-refusal guards, replacing the server rebuild clock. Matches the record.

## R-2 · Acceptance bar ("actually fixed") — **RATIFIED (strict)**
Verbatim: "Strict definition" → confirmed post-disclosure.
Victory requires a scheduled run whose pass demonstrably comes FROM the new
check (disposition=GATE on the content axis), cross-checked against the
producer's same-trace record, with deploy-adjacent and old-fallback passes
worth zero, no synthetic warming, no threshold moved. Matches the
change-warden's honest REALIZE predicate.

## R-3 · Delivery path — **RATIFIED (repair the pipeline)**
Verbatim: "Repair the pipeline" → confirmed post-disclosure including the
timeline-coupling consequence (fix cannot reach production until the publish
pipeline is repaired; lead time unestimated). Fire
HANDOFF-10x-dev-to-releaser-2026-08-11.md. NO local duplicate (Lane J stays a
priced fallback only). Matches the record.

## R-4 · Approach reversal triggers — **RATIFIED as REVIEW-PROMPTS**
Any of: a false-fresh pass · a refusal storm on healthy runs · the
edit-timestamp column proving unreliable → triggers a REVIEW, not an automatic
halt. (Operator explicitly chose review-prompts over halt-triggers.)

## R-5 · FIX-N merge admits — **RATIFIED (admit at gate-clear, automatic)**
Verbatim: "Admit at gate-clear" → confirmed post-disclosure that this is MORE
permissive than the record's operator-admit posture. Both service-repair PRs
(asana #338, #339) merge automatically once ALL gates are satisfied:
(a) P5 window closed (≥2026-08-12T09:19:45Z); (b) the consuming job's C-NULL
fix DEPLOYED (strict deployed-image reading); (c) R-7's rollback runbook
written; (d) #338's re-adjudication inscription conditions (already in its
body). No further operator check-in at merge time.

## R-6 · Build-order enforcement — **AMENDED (honest quiet tolerance)**
Original answer "Prefer quiet tolerance"; after disclosure of the silent-dark
consequence of naive quiet, operator chose: **"Honest quiet tolerance"** —
REMOVE the hard >=4.14.0 build-failure floor; the job instead
CAPABILITY-DETECTS the installed library and, when the content axis is
unavailable, falls back to the old clock WITH a visible disclosure log (never
silently dark, never a build failure). This amends the as-built K-ASR leg:
one additional build task + a QA delta pass over the change are required
before that leg's merge. The forced merge ORDER (SDK → publish → ASR) remains
operationally preferred but is no longer build-enforced.

## R-7 · Rollback preparedness — **RATIFIED (precondition)**
The written image-level rollback runbook is a REQUIRED PRECONDITION of the
merges (not a fast-follow). Matches the record, elevated to binding.

## R-8 · Post-deploy rollback triggers — **RATIFIED (asymmetric)**
Roll back on: serving-path latency/availability regression OR new
refusals/errors at the consuming job. Other unexpected-but-harmless behavior
deltas → review first, not rollback. Asymmetry explicitly confirmed.

## R-9 · Alarm binding — **AMENDED POST-DISCLOSURE: FIRE NOW**
Initial answer "Hold until cure lands"; on disclosure of the record's
rationale (honest floor, window-independent, third occurrence of the
silent-alarm class), operator changed to: **"Fire it now"** — execute the
scoped, targeted apply per CARD-l6-alarm-apply-2026-08-11.md §4 (Option A:
bind to autom8y-platform-alerts), today. This is explicit operator
authorization for that apply and only that apply.

## R-10 · Rename — **RATIFIED**
Forward name: **offers-freshness-axis-contract**. Past artifacts keep their
names; all new artifacts, branches, and bookkeeping use the new slug.

## R-11 · Freshness-tolerance ownership — **RATIFIED (deliberate deferral)**
Decide the single-source question AFTER the new check is deployed and
observed. Both one-hour numbers stand as-is; the unmeasured 60s clock-skew
allowance and the HELD-2 field-naming choice ride to that same future
decision (card D-5b). Matches the record.

## R-12 · Follow-up initiatives — **RATIFIED (three opened, trio deferred)**
OPEN now as standalone items: (1) silence/cadence-absence alert for scheduled
internal consumers; (2) failure-forensics log field (FAILED runs carry the
same timing evidence as PASSes); (3) capacity early-warning metric (headroom
vs the 1000-row cap). The infra hygiene trio (untracked live alarm file ·
contested alarm reading · #312 debt note) is **DEFERRED — kept on the stack,
unopened**, to resurface at the next review; explicitly NOT declined.

---

Interview discipline notes: recommendations were withheld until after each
answer; two answers changed on disclosure (R-6 to the honest-quiet shape,
R-9 to fire-now); one ruling is more permissive than the record (R-5,
confirmed knowingly); no HOLD was recorded; no ruling was inferred.
