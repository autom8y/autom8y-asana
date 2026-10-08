# RATIFICATION — decision-space sitting IV, 2026-09-09 (evening)

**Form:** `/interview`, two adaptive rounds, seven questions. **Rulings R-99 … R-104.**
**Selection: 4 of 7 took this seat's recommendation; 3 did not.** Never-grantable floor **UNTOUCHED**.

---

## §1 DECIDED

### R-99 — R-35 LIFTS NARROWLY: `services/email-booking-intake/**` only · BINDING
The freeze's question is discharged (the hotfix was inert and superseded). **The gate stays landed and
UNARMED**, to be armed later. **The operator rejected this seat's recommendation** to require arming
first. **Accepted cost, printed in the option and chosen anyway:** *"arm it later is exactly how a
control stays unarmed forever."* R-99 sequences the two costs rather than paying both at once.

### R-100 — R-97 IS FULLY RETROACTIVE; the object-store residue is ACCEPTED · BINDING
All three artifacts are rewritten to token form. **The operator was told, and ruled anyway, that a
force-push does NOT purge** — proven today by `e2b57fde` — so pre-redaction objects persist.
**The operator rejected both the GitHub-support purge and deleting PR #423.**
> **Ruling of record: the READ path becomes correct; the object store is knowingly left inconsistent.
> "Withheld" is true of what anyone will read, and not true of what a determined reader can fetch.**
**This seat's omission, recorded:** the first round asked the scope question **without stating that
retroaction requires an external purge.** The operator ruled once without that constraint and once
with it.

### R-101 — The fifth face: MEASURE the trace's coverage BEFORE framing anything · BINDING
Of the 42 allowlisted offices, how many carry an ask-shaped Asana story? **This tests THIS SEAT's
claim, not the operator's** — *"promotion not construction"* is currently an inference from **N=1**.

### R-102 — CHASE whether the six divergences SHOULD have landed · BINDING
Read-only: for each, was there a lead, a valid appointment window, and a reason to refuse?
**Declared risk, accepted:** it may conclude all six were correctly refused, **in which case the day's
most alarming number evaporates.** The operator took that trade knowingly.

### R-103 — The arming trigger gets an INSTRUMENT, not an intention · BINDING
Trigger: **open PRs touching `services/**` that predate the gate**, below a threshold **N**.
**Owner: the operator (to arm). Instrument: this seat (to measure and surface).**
**`[OWN-HANDS]` basis, measured at ratification:** 63 open PRs · **33 touch `services/**`** ·
17 touch EBI · **32 of the 33 PREDATE the gate and would block when armed.**
> **★ N IS NOT YET NAMED. THIS SEAT PROPOSES N = 10** — i.e. arm when predating-`services/**` PRs fall
> below ten. **PROPOSAL ONLY; unconfirmed.** Leaving N unnamed would reproduce, for the third time,
> the exact defect R-35 was faulted for.

### R-104 — EBI merge order under the narrow lift · BINDING
1. **#2073 → main** (apply #1) · verify live
2. **retarget #2105 → main**, merge (apply #2) · verify live
3. **reassess #2071**
**C-1's one-image-event law holds: each merge is a separate apply and they are NOT bundled.**

---

## §2 DEFERRED
The identity spine · F-1…F-7 · clause (c2) · O-2 §A, O-4(a)(b)(c), O-7 · the PII cure · the second
`phone_hash` instance · `calendly-intake-recon` (the strongest client-path candidate among the 12
disabled rules) · whether the ad-lead-gate's refusals are all *correctly* refused.

## §3 ASSUMPTIONS UNCONFIRMED
1. **★ N is unproposed-and-unratified.** R-103's instrument has no number until the operator sets one.
2. **★ Whether C-13 is discharged.** The 18:00Z cut passed and the rows survived; the cofounder
   exchange happened. **R-87 makes C-13 dominant over R-74's legs, and only the operator can say
   whether that exchange WAS C-13's conversation.** **If it was not, R-99's lift may be premature.**
3. **`is_paying = 0`** on all four divergence offices — field semantics and snapshot currency both
   unverified.
4. **The fifth face's cheapness** rests on **N=1**. R-101 exists to test it.
5. **R-100 leaves a knowingly-inconsistent object store.** A future reader who fetches rather than
   reads will find the names.

## §4 WHAT SITTING IV DOES NOT DO
It does not arm the gate, discharge C-13, close clause (a) or (c2), or cure the PII.
**It discharges no clause — all four remain WAITING.** Clause (b)'s **naming** half is landed
(`7e080677`); its **emission** half is #2105 and is still parked.

> **`Verified-realized` = a LIVE attributed booking naming that office, TWO-SIDED — a failure for the
> SAME office also names it, WITH ITS KIND, never blank — held across ALL active clients, not one.
> NOT "PRs merged". DONE IS A BAR, NOT A DATE.**
