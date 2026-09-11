# RATIFICATION — Decision-Space Sitting VIII (the day after)

**Date:** 2026-09-10 (~17:45Z) · **Seat:** calendar-integration-locus
**Purpose:** ratify today's work after the overnight push and pythia's day-after consult.
**Selection pattern: 7 of 7 recommendation-bearing questions DISPLACED the seat's recommendation,
one by premise rejection.** Recorded as calibration: the seat's read of the operator's appetite ran a
full notch conservative today. The recommendations were not adjusted to chase it.
**Named consumer (R-88):** any seat that finds NULL offers resolving as ENABLED, a SEV-1 alarm
retired, or `nhc-db` open to the internet, and cannot see this room.

---

## §1 RULINGS R-123 … R-131

| # | ruling | displaced? |
|---|---|---|
| **R-123** | **Today is a BUILD day.** "The product moves." Containment is not today's bar. | YES |
| **R-124 ★** | **`nhc-db` exposure is KNOWN AND ACCEPTED.** Default SG `sg-e2e313a7`, `IpProtocol=-1` from `0.0.0.0/0` + `::/0`, `PubliclyAccessible=True`, resolves to `54.158.189.130` — verified own-hands by two seats. **Legacy monolith access, understood risk. Carrier #10 CLOSED as accepted.** Both seats that ranked it first were wrong to; the next seat must not escalate it a third time. | YES |
| **R-125** | **The overnight grant is STANDING into today.** R-120 (deploy-inert anywhere + `services/email-booking-intake/**`) and R-122 (`autom8y-scheduling` full authority) carry forward. **Terraform apply is NOT covered** — seat's reading, unconfirmed (§3). | YES |
| **R-126** | **REPLACE the deadman, in ONE apply.** Retire `ebi-sparse-tail-liveness-dark` (metric `EbiPipelineCompleted`, which rose 297→5,070/day during the 3.7-day zero-booking outage — verified own-hands) and floor `EbiBookingPosted` (0.0 for 08-23/24/25 — verified). Metric filter ↔ log event 1:1 must be proven before the floor lands. | YES |
| **R-127 ★** | **F-2 PREMISE REJECTED.** *"The sections you're mentioning are BusinessUnit entity sections, which does not provide an accurate read of status, which comes from section groups defined in the Offer entities."* The two disagreeing vocabularies may be reading the WRONG GRAIN. Routed to `identity-activity-substrate-build-wave2` with four file:line questions. **Nothing on clause (d) moves until it answers.** | premise |
| **R-128 ★★** | **NULL MEANS ENABLED. Flip the default, ALL AT ONCE.** `offer_resolution.py:98` `scheduling_enabled = offer.disabled == False` reverses the ADR's "conservative default" (NULL→disabled). Bounded to businesses WITH a NULL offer row; the 750 with no rows never reach that line. **The affected set is MEASURED before merge** as a receipt, not as a rollout gate. | YES |
| **R-129** | **Today's build, ALL FOUR:** wire the fourth leg (blocked on R-127) · replace the deadman · name the two blank siblings (`ad_lead_gate_refused`, `booking_intake_fault` — 73 unnamed/12h, growing) · the NULL-shadow (folded into R-128's tests, see §3.4). | multi |
| **R-130** | **Proving (d): DRY-RUN FIRST.** The hook computes and logs verdicts without refusing; **flips to enforce on a COUNT of N verdicts of each kind.** | YES |
| **R-131** | **N is UNNAMED.** The seat proposes **N=3 each** and will NOT wire the auto-flip until the number is confirmed in this room. | — |

---

## §2 DEFERRED
- The fourth leg's referent → substrate session's grain answer.
- The alarm **apply** → operator word.
- **N** → operator word.
- The identity one-pager (F-1…F-7, R-110) → not raised today.

## §3 UNCONFIRMED
1. **N.**
2. That the grain correction DISSOLVES the fork rather than relocating it to the Offer grain.
3. The NULL-flip affected-set size (measured before merge; not assumed).
4. That folding the NULL-shadow proof into R-128's tests is acceptable — under NULL→enabled a NULL row resolves enabled and cannot shadow-refuse, so the "fix" becomes a test that it resolves enabled.
5. The seat's reading that R-125 excludes terraform apply.
6. **7/7 displaced.** Equally consistent with a conservative seat and with an operator choosing speed on a day after a long night. Recorded, not resolved.

## §4 CORRECTIONS CARRIED INTO THIS SITTING
- pythia's day-after consult corrected the seat on two material points, both verified own-hands: the deadman is INVERTED (not "unextended"), and `nhc-db` was understated. **R-124 then overruled the ranking of the second.** pythia also closed carrier #8 for free (**CURE, not silent loss**) and adjudicated its own prior consult: five held, two wrong (the 663 double-count; "missing primitive" wrong in location).
- The seat's own three assumptions rejected today: the grant expired at dawn (it didn't); the DB exposure was unintended (it's accepted); F-2 could wait (the premise was wrong, not the timing).

---

## §5 ADDENDUM — rulings after the substrate answer (~19:30Z)

| # | ruling | displaced? |
|---|---|---|
| **R-132 ★** | **The fourth leg's referent: BUILD THE BUSINESS AGGREGATION FIRST**, over the OFFER grain. The substrate session measured (asana `origin/main`, file:line): the two disagreeing vocabularies are genuinely BusinessUnit-grain (project `1201081073731555`) and genuinely disagree — but one is a status source and the other a frozen monolith routing table + drift detector, never built to agree. **The fork dissolves by JURISDICTION**: R-127 rules that grain non-authoritative. On the Offer grain there is exactly ONE vocabulary — `OFFER_CLASSIFIER` (`activity.py:181-210`, project `1143843662099250`) — and it carries `activating = {ACTIVATING, IMPLEMENTING, NEW LAUNCH REVIEW}`. **No offer→business aggregation existed on main** (taken zero: searched three repos, positive control `max_unit_activity` found by the same pattern). The operator: *"it should be obvious and I'm not convinced this doesn't already exist"* — the obvious rule IS the unit one, applied to offers. **Built as `Business.max_offer_activity`, `autom8y-asana` PR #431, PARKED** (asana source is not deploy-inert). Two-sided: 48 / 6 RED on removal / 48. | YES — seat recommended per-offer, no aggregation |
| **R-133** | **N = 3 verdicts of each kind** before the dry-run flips to enforce. Matches the seat's R-131 proposal. Confirmed. | — |
| **R-134 (seat deviation, flagged)** | R-126 said "floor `EbiBookingPosted`." That metric's filter (`contente_booking_booked`) is **not 1:1 with its own event day-to-day** (±1–2 on volumes of 1–7; pythia's caveat confirmed own-hands) and at 1–7/day a floor of 1 would false-page on quiet days (09-07 = 1). **The seat is flooring `booking_attempt` instead** — 30–90/day, the pattern proven 1:1 (90=90, 17=17, fabricated 0=0), and **it went 31 → 10 → 0 → 0 across 08-22..25** while the retired metric climbed to 5,070. Same intent, different metric; **one line to reverse** if the operator wants `EbiBookingPosted` specifically. Built as `autom8y` **PR #2165**; merge is plan-only; **apply is the operator's word.** | deviation |

**Section-timeline note (substrate pointer, read):** `section_timeline.py` is a retrospective interval tracker — its own docstring says moved/never-moved are indistinguishable in day counts — **not a live hook.** The fourth leg needs its own binding.
**Third-family flag (carried, not resolved):** the substrate's account model of record (`account_status`, `source='section_classifier'`) is keyed by `pipeline_type` → the process-pipeline classifier family, **not** the Offer grain. Two predicates, one name. Recorded so someone reads it.

## §6 EXECUTION RECEIPTS — the day's landings under R-125
| item | where | receipt |
|---|---|---|
| **NULL → enabled (R-128)** | `autom8y-scheduling` `95c19608` (#76) | two-sided 70 / 3 RED / 70 · affected set measured before merge: 12 clinics, 27 refusals/24h · ECS td `:268` PRIMARY COMPLETED **19:11:14Z**, image `95c1960` · live receipt: **zero `scheduling_gate_rejected` of any class since rollout, 7 `booking_success` as traffic control** (60 records, own-hands, single read). The two refusals at 18:13Z/18:24Z predate rollout (old task). Positive half — the twice-refused clinic `…4776` passing — organic, not yet observed. |
| **blank siblings named (R-129)** | `autom8y` `4deffb38` (#2149) | 362 / mutant A 3 RED / mutant B 2 RED / 362 · declared cross-stack divergence recorded in the guard · Lambda image `4deffb3` live 19:04:26Z · live receipt: **`ad_lead_gate_refused` 5 named / 0 blank since** (178 records, own-hands, single read) |
| **offer-grain aggregation (R-132)** | `autom8y-asana` **PR #431 PARKED** | 48 / 6 RED / 48 · asana source is not deploy-inert; operator merges |
| **deadman replaced (R-126 / R-134)** | `autom8y` **PR #2165** | 23 / 10 RED on the old tf / 23 · `terraform fmt` clean · **auto-merge armed**, pending only CodeQL `Analyze Python`; main moved under it four times · merge is plan-only; **one apply is the operator's word** |
| **fourth leg wiring** | — | NOT STARTED. Waits on #431 landing (the aggregation the referent needs) and on the dry-run binding to the Offer grain. N=3 (R-133). |

---

## §7 CROSS-ARC CLOSURE — the placeholder-phone class (vertical-summary session, C4S-R208 → C4S-R215)

**Read-only exchange, both directions; no count moved; no office phone on any face.** Their spike:
`.ledge/spikes/SPIKE-placeholder-phone-root-cause-2026-09-10.md` @ `c83170b8`, branch
`vertical-summary/c4-cure-charter` — cited, not duplicated.

**What this seat measured for them (own-hands, origin/main):**
- Scheduling writes `appointments.phone = lead_phone` verbatim — `scheduling/booking.py:191-193`; no office-phone fallback, no default contact.
- EBI sends `lead_phone = ctx.resolved_phone` (`book_appointment.py:161-162`), refuses to book without one (`:108-109`), and sets it at **`match_lead.py:1029` `ctx.resolved_phone = ctx.contact_phone`** right after creating the lead on the same field. **No guard that `contact_phone != office_phone`** — zero exclusion forms across `extract_fields.py` / `match_lead.py` / `extraction/*`, control `office_phone` firing at `match_lead.py:1140`.
- gcal never creates appointment rows: `gcal_sync.py:524 _store_event_id` / `:560 _clear_event_id` are `select … where` + update; the only `insert` is Google's `events.insert` (`:172`).
- **The modern GHL binding is dark scaffolding:** `ghl_sync.py:44 GHL_AVAILABLE = False`; create call + `_store_ghl_event_id` commented out (`:99-122`); `_store_ghl_event_id` (`:372`) has ZERO live callers; no writer of `appointments.ghl_event_id` in scheduling / autom8y / autom8y-data at main. The SDK (`autom8y/sdks/python/autom8y-ghl`) parses `contactId` (`Appointment.contact_id`, required on create) and exposes `appointments.get(event_id)` → `GET /calendars/events/appointments/{event_id}` — but is a dependency of nothing and installed in no venv.
- **`Lead.ghl_contact_id` ALREADY EXISTS** — `models/shared.py:82` class, `:164` field — declared, never read or written in any of the three repos. A dark column, on the right table.

**What their data established (theirs, cited):** the office-phone class spans 58 months (2021→2026), ten-plus lead writers, **1,104 distinct real people** whose phone field holds the clinic's number. EBI is a **carrier since 2026-04-12, not the origin.** Originators are upstream in `contente-legacy@e616180ff` (Heroku): **A1** `server/api/website/onboarding.js:255-261` — one placeholder lead per onboarded office, phone = office phone; **A2** `models/leads.js:289-306`; **A4** the LLM extractor lineage (n8n → monolith `booking_handler.py` 2024-03 → EBI), unverified because it is an LLM. Shape B (thousands of events on one phone) is the `/calendar/reviewwave` path driven N times (`model/appointments.js:46-51`, `scheduler.js:371-413`) by the `notify-reviewwave` Lambda whose source is in no checkout — not an intake defect, not office phones.

**Operator disposition (theirs, C4S-R215):** the office-phone class is OUT as a disclosed data-defect exclusion, never "unattributed"; **the re-arm trigger is THIS SEAT carrying GHL contactId forward**; A1/A4 are the named upstream cures.

### Defer registry additions (namespace RATIF-VIII)
| id | item | waits on | watcher |
|---|---|---|---|
| **RATIF-VIII-A4-EDGE** | `contact_phone != office_phone` guard at `match_lead.py:1029` — A4's downstream edge. **In-grant, deliberately NOT built:** refusing a mail whose only number is the clinic's is a product disposition (is it a booking at all?), and the HealthCom body-retain lever (#2169, name-the-wave) answers that before anyone writes a refusal. | a disposition on the HealthCom class | **name-the-wave** (bodies) · this seat (guard) |
| **RATIF-VIII-CONTACTID** | Carry GHL `contactId` forward: populate dark `Lead.ghl_contact_id` (zero schema) · one column + migration on `appointments` · **un-scaffold the dark binding first** (`GHL_AVAILABLE`, SDK dependency, create call). C4S-R215's re-arm trigger. | an operator word; larger than a column, smaller than a design | **vertical-summary session** (re-arm) · this seat (build) |
