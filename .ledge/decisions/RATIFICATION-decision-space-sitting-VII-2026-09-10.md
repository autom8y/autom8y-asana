# RATIFICATION — Decision-Space Sitting VII (the overnight grant)

**Date:** 2026-09-10 (~02:40Z) · **Seat:** calendar-integration-locus
**Purpose:** unblock an unattended overnight push with maximum alignment. Two rounds, eight questions.
**Named consumer (R-88):** every seat that finds this seat merging in `autom8y-scheduling` or in
`services/email-booking-intake/**` overnight and cannot see this room. **Read this before assuming a
collision.**
**Selection pattern:** round 1 = 4/4 took the recommendation; round 2 = **2/4 displaced it**. The
lead-the-witness risk sittings I and V flagged is present in round 1 and broke in round 2.

---

## §1 ROUND ONE — RULINGS R-112 … R-115

| # | ruling | displaced? |
|---|---|---|
| **R-112** | **V13: RECORD the three modules.** Executed — landed as `47f50912` (another seat, byte-identical to this seat's #2135, which was closed as superseded). V13 PASS 20/20 on main; `module-consumers serving-color-alarm` → 7 services. | matched |
| **R-113** | **Telos: AMEND to match rulings.** Executed — `83a9ae99` (#427). (c) split into (c1)/(c2) per R-78; (c1)=1 per RATIF-VI-D1. **"All active clients" survives in full as (c2), BOOKED OPEN.** | matched |
| **R-114** | **Finish line: VERIFY, then close.** Dispatch the rite-disjoint attester. *(Refined by R-116 below.)* | matched |
| **R-115** | **Not-enrolled: INVESTIGATE now.** | matched |

## §2 ROUND TWO — RULINGS R-116 … R-119

| # | ruling | displaced? |
|---|---|---|
| **R-116** | **Clause (d): BUILD THE FOURTH LEG FIRST**, then verify all four. A three-of-four verdict is UNATTESTED by the wave's own rule; the operator chose to close that gap rather than scope around it. | **YES** — seat recommended scoping to three |
| **R-117** | **Manifest edit: BUILD AND MERGE.** (Executed via R-112's landing.) | **YES** — seat recommended build-only |
| **R-118** | **Enrollment truth: SPIKE the scheduling repo directly** (`autom8y-scheduling`) and review its `.know/`. Executed — `SPIKE-scheduling-enrollment-truth-2026-09-10.md`. | modified option 3 |

## §3 ROUND THREE (the overnight sitting) — RULINGS R-119 … R-122

| # | ruling | displaced? |
|---|---|---|
| **R-119** | **Clause (d) tonight: MEASURE the `activating` vocabularies; the OPERATOR RULES F-2 AT DAWN.** Per R-111 §4: *this seat measures, THEN the operator rules.* Clause (d) is NOT built tonight. | matched |
| **R-120 ★** | **OVERNIGHT MERGE AUTHORITY: deploy-INERT anywhere, PLUS service code in `services/email-booking-intake/**`.** Every merge still requires: all checks green · no bundling · nothing merges past red · one image event per merge. | **YES** — seat recommended inert-only |
| **R-121** | **Tonight's threads, ALL FOUR:** the not-enrolled split · the instrument census · the record corrections · the independent check. | (multi-select) |
| **R-122 ★** | **`autom8y-scheduling`: FULL AUTHORITY** — build, merge, deploy. | **YES** — seat recommended read-only |

### §3.1 How this seat reads R-120 × R-122 — stated so it can be corrected in one line
R-122's option text read *"subject to whatever you answered on merging."* R-120 names `email-booking-intake`
and does not name `scheduling`. Read literally, R-122 would collapse to build-and-park. **This seat reads
R-122 as a SPECIFIC grant that extends R-120's list** — specific overrides general — because the operator
chose the most permissive option for that repo immediately after choosing a bounded one in general, and
the alternative reading makes the choice meaningless.

**Self-imposed split within R-122, on risk, not on authority:**
- **The discriminator logging** (log `offer_guid` on the refusal so absence and decision separate) —
  purely additive log field, same shape as #2073/#2125 which both landed clean tonight. **Build, prove
  two-sided, merge, deploy, verify live.**
- **The NULL-shadow resolver path** (`offer_resolution.py:38` vs `:98`) — changes WHICH OFFER RESOLVES,
  i.e. whether real bookings succeed, on a path every existing test mocks out. **Characterize, write the
  test that proves it either way, PARK the fix unmerged.** An unattended behaviour change to the
  appointment-booking path is not something this seat will take on an inferred reading.

## §4 UNCHANGED BY THIS SITTING — THE FENCES THAT STAND
- **Never-grantable floor:** rotation-execution · customer-visible outbound acts · business-of-record
  identity mints. **Not asked for. Not granted. Not touched.**
- **Freeze gate / ruleset 17263542:** untouched in either direction absent a direct operator word in
  this seat's own room. **Not asked for.**
- **Nothing merges on a relay · nothing bundles · nothing merges past red.** R-120 is a grant of
  *standing* word for a bounded set; it does not lift any of these.
- **R-80 ROLL-FORWARD-ONLY, NO RESTORE.**
- **Attestation:** neither this seat nor any peer declares a clause closed. R3 attests; R2 has now
  fired (R-113), so the attester grades against the current bar.

## §5 EXPLICITLY DEFERRED
- **F-2** (which `activating` vocabulary governs) — measured tonight, **ruled at dawn**.
- **Clause (d)** — blocked on F-2. Foundation exists (`b17a066c`, NOT WIRED, no default referent by design).
- **The NULL-shadow fix** — characterized tonight, **merge word at dawn**.
- **R-79's second two-sided office** — a bonus, not a bar (RATIF-VI-D1).

## §6 ASSUMPTIONS UNCONFIRMED
1. **The §3.1 reading of R-122.** If wrong, the discriminator merge is an unauthorized production deploy
   to the booking service. **The operator can correct it in one line; this seat will not proceed to the
   merge step until the build is green and has re-read this room for a correction.**
2. That R-120's "booking service" means `services/email-booking-intake/**` in `autom8y` and not the
   scheduling service. The option text named email-booking-intake; this seat holds to that.
3. That the four threads in R-121 can run concurrently without a shared upstream. They share CloudWatch
   reads, which is safe, and share no writes.
4. **4/4 then 2/4.** Round one's clean sweep is recorded as a caution; round two breaking it is the
   evidence that the framing was not simply leading.
