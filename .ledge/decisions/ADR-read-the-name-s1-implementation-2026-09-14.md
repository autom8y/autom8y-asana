---
id: ADR-read-the-name-s1-implementation-2026-09-14
date: 2026-09-14
status: ACCEPTED-BY-DELEGATION (sitting XI, operator delegated implementation forks to the seat + architect)
initiative: read-the-name
wave: 1
self_cap: MODERATE
---

# ADR — `read-the-name` wave 1 · S-1 per-office booking floor · IMPLEMENTATION RULINGS

**Scope.** This ADR rules the EIGHT forks the operator delegated at the S0b sitting (D1–D8).
It does **not** rule the four value forks held by the operator (consumer word · page-repeat
policy · smoke-lead practice · WS-2 sequencing) — those are being asked in parallel and D7
below is deliberately mechanism-only.

**Standing rulings this ADR is built on and does not re-open:** R-150 (Shape A logs-native
evaluator; W = 3 days rolling; A = 5; bookings floor 0; the page carries the Offer-grain class) ·
R-154 (consumer = `platform_alerts`, business hours) · **R-160** (the floor has TWO page classes in
one evaluator — a ZERO floor and a RATE floor, each its own page class and its own probe at S1.4) ·
telos Laws (consumer before instrument · own silence deadman · never blank · untaken-zero) ·
charge §3 (metric filters are not retroactive; any new metric soaks ≥ 7 d before its alarm arms;
a prober-published gauge has datapoints from apply-time).

---

## §0 REFS, METHOD, LABELS

**Refs named (STALE-TREE; every code/terraform read is `git fetch origin main && git show "origin/main:<path>"`):**

| repo | path on this machine | `origin/main` at authoring |
|---|---|---|
| `autom8y-asana` | `/Users/tomtenuta/Code/a8/a8/repos/autom8y-asana` | **`49506a21`** |
| `autom8y` | `/Users/tomtenuta/Code/a8/a8/repos/autom8y` | **`a1f3ecf3`** |
| `a8` (module source) | `/Users/tomtenuta/Code/a8/a8` | **`2b7c00d`** |

> ⚠ **Correction to the S0a packet.** The packet names `autom8y origin/main = b70861be`. Fetched
> at this authoring it is **`a1f3ecf3`**. Every `autom8y` claim below was re-read at `a1f3ecf3`;
> no claim in this ADR is inherited from the packet's stale ref. (Per charge §7 STALE-TREE.)

No reads under `.knossos/worktrees/` or `.terraform/`. No phone digits, no raw client names —
guid8 prefixes only. No writes outside this one file. No commits, no applies, no AWS mutations
(every AWS fact below is inherited from the read-only replay measurements taken by the main
thread this morning, or from pythia's `describe`/`get`/`list` ledger).

**Evidence label on every ruling:** `VERIFIED` (own-hands read at a named ref, or a measurement
this seat consumed with its command shape stated) · `INHERITED` (asserted by a prior artifact,
not re-derived here) · `UV-P` (unverified premise, frozen syntax, carried to §11).

**Self-cap: MODERATE** (single seat, no rite-disjoint corroboration — `self-ref-evidence-grade-rule`).

---

## §1 THE THREE MEASURED FINDINGS THAT BIND EVERY RULING BELOW

These were not available to the S0a packet or to pythia. Each changes an answer.

### FINDING-1 — **The ruled ZERO floor does not fire on the founding office.** `[VERIFIED]`

`ccb52f4c` has **4 / 4 / 1 `booking_completed`** in the 8-day, 3-day-B and 3-day-C windows
respectively (0 `contente_booking_booked` in all three). It is **not at zero bookings in any
window.** Under R-150 as written (`arrivals ≥ 5 AND bookings = 0`) the instrument built to name
`ccb52f4c` **would never have named it.**

Simultaneously, a zero floor at A = 5 fires **15 offices in 8 days** (8 in window B, 4 in window C),
including the unattributed `***` bucket, the disabled office `40f86e73` and the malformed-guid
office `e5a68603`.

⇒ R-160's two-class split is not a refinement; it is what makes the instrument able to do its
founding job at all. The **RATE floor is the primary class**; the zero floor is the secondary.

### FINDING-2 — **The decline line is retry-inflated BY DESIGN, and the service says so.** `[VERIFIED]`

`autom8y origin/main:services/email-booking-intake/src/email_booking_intake/park.py`, verbatim at
the `terminal_decline` emitter: *"(1) Structured observability event -- ALWAYS, on every delivery.
A re-delivery logging again is DESIRABLE: it shows the retry-churn being absorbed."*
And at the `terminal_decline_parked` emitter, verbatim: *"The ``terminal_decline`` event above
fires on EVERY delivery and is thus retry-inflated while the SendGrid pool drains; THIS line
additionally carries ``newly_recorded`` so a CloudWatch metric filter keyed on
``newly_recorded=true`` counts DISTINCT parked mails -- the precise F-SOAK-09 realization signal,
not the retry-churn dashboard count. … this is the DISTINCT-mail line (retry-deflated), so it is
the one an operator counts per client. Naming the office here is what makes "which clinics are
losing mail" answerable at all."*

Two consequences:
1. **`terminal_decline_parked` CO-OCCURS with `terminal_decline` for the same mail** — both are
   emitted inside the same park path (steps (1) and (3b) of the same function). The packet's F10
   UV-P is **discharged VERIFIED**: summing them double-counts.
2. **A line count is a delivery-churn count, not a mail count**, and the inflation is
   *per-office variable*: measured over the 8-day window, `ccb52f4c` = 580 lines / 329 distinct
   `message_id` (**1.76×**) while `c2ab6637` = 145 lines / 9 distinct `message_id` (**16.1×**).
   A threshold of "5" therefore means a different number of mails for every office — a
   construct-validity failure at the denominator (`assessment-methodology` P-07/P-08), not a
   rounding detail.

### FINDING-3 — **No uniform correlation field exists; each id is path-specific.** `[VERIFIED]`

Over the 8-day window, per office: `ccb52f4c` = 3 distinct `lead_id` / 329 distinct `message_id`;
`c2ab6637` = 17 / 9. **Six** of the top-25 offices have **0 distinct `message_id`** with non-zero
lines (`8e56f6e1`, `53295a22`, `933a026c`, `4a2f351c`, `9fcf1507`, `40f86e73`); **eight** have
**0 distinct `lead_id`**. `message_id` rides the decline path (`park.py` logs
`message_id=ctx.message_id` on `terminal_decline`); `lead_id` rides the ad-lead path.

⇒ A "distinct correlation id" arrival unit **silently zeroes whole paths**: an office whose events
are bookings and gate-refusals gets `arrivals = 0`, can never cross any floor, and — worse — has a
**zero denominator** for the rate floor. That is structural blindness located exactly at the
number the instrument exists to compute.

### FINDING-4 (bonus, consequential) — **The founding count is not reproducible.** `[UV-P → §11]`

The charge §1 founding instance is *"406 inbound mails, 2 completed bookings, eight days"*. The
8-day window measured here (09-04..09-12, the same 8 days) yields **580 office-bearing lines,
329 distinct `message_id`, ~352 terminal-outcome mails, and 4 `booking_completed`** — none of which
is 406, and none of which is 2. **A = 5 was calibrated against a predicate that cannot be
recovered from the log plane.** This ADR therefore re-derives the thresholds against *measured*
quantities and states the arithmetic, rather than inheriting a number whose unit is unknown.

---

## D1 — F10 · THE ARRIVAL UNIT, AND THE TWO FLOORS' PARAMETERS

**The business meaning to be realized:** *one inbound email attributed to that office*.

### D1.1 Terminal outcomes — the enumerated set `[VERIFIED at autom8y a1f3ecf3]`

A **terminal outcome** is a log event that represents a *pipeline terminus for one mail*.
Emitter sites read at `origin/main` (`git grep -nE '"(…)"' origin/main -- services/email-booking-intake/src`):

| event | emitter | terminal? | reason |
|---|---|---|---|
| `terminal_decline` | `park.py:173`, `pipeline/stages/book_contente.py:534`, `:820` | **YES** (retry-inflated) | the decline terminus; fires on every *delivery*, carries `message_id` |
| `ad_lead_gate_refused` | `ad_lead_gate/observe.py:60`, `pipeline/context.py:38` | **YES** | gate terminus |
| `booking_gate_declined` | `pipeline/stages/book_appointment.py:183` | **YES** | booking-gate terminus |
| `booking_completed` | `pipeline/stages/book_appointment.py:228` | **YES** | success terminus (scheduling door) |
| `contente_booking_booked` | `pipeline/stages/book_contente.py:928` | **YES** | success terminus (convergence write) |
| `booking_intake_fault` | `intake_loss_count.py:135` | **YES** | fault terminus |
| `terminal_decline_parked` | `park.py:393` | **NO — SECOND LINE for a mail already counted** | co-occurs with `terminal_decline` in the same park path (FINDING-2) |
| `stage_exception` | `pipeline/orchestrator.py:223` | **NO** | an exception *inside* a stage; the mail still reaches a terminus |
| `contente_two_writer_overlap` | `pipeline/orchestrator.py:371` | **NO** | a concurrency warning, not a terminus |
| `booking_contente_stage_failed` | `book_contente.py:379` | **NO** | a stage failure; followed by a decline/park |

### D1.2 RULED: arrival unit **U-3** — terminal outcomes, de-duplicated by `message_id` where present

```
arrivals(office, W) = A_id + A_noid

A_id   = count_distinct(message_id)   over office-bearing lines in W where message_id IS present
A_noid = count()                      over office-bearing TERMINAL-OUTCOME lines in W
                                       where message_id IS ABSENT
bookings(office, W) = count_distinct(message_id | line) over
                       { booking_completed } UNION { contente_booking_booked }        [P3, union]
```

**Why this realizes the business meaning uniformly.** Where the mail has an identity, the identity
*is* the unit — exact, retry-deflated, immune to the `terminal_decline`/`terminal_decline_parked`
double-count. Where it does not, the fallback counts **termini only**, never every line, so the
`stage_exception`/park inflation is not re-imported through the back door. The fallback is a
*bounded* degradation of one unit, not a second unit.

**Consequence worth stating: U-3 makes `A = 5` mean what the sitting thought it meant.** R-150's
"A = 5" was set against "406 **mails**". Under U-3 the threshold is five *mails*. Under any
line-count unit it is five *log lines*, which for `c2ab6637` is roughly one third of a mail.

**Booking predicate = P3 (the union `booking_completed ∪ contente_booking_booked`).** RULED: the
floor must be **hard to trip**; any evidence of a booking silences it. Missing a booking produces a
**false page**, which is the expensive error for a consumer whose attention is the scarce resource.
Rejected: **P1 only** (`contente_booking_booked`) — measured 0 for `ccb52f4c` in every window while
`booking_completed` = 4, so P1-only would have mis-classified the founding office as a *zero*, not a
*rate*, case. Rejected: **P2 only** (`booking_completed`) — `d167d635`, `4ec260bf`, `ca70baa8`,
`8e56f6e1` all carry non-zero P1, so P2-only understates their denominators and pulls quiet offices
toward the floor.

### D1.3 Rejected arrival units, each with its reason

| # | Unit | REJECTED because |
|---|---|---|
| **U-1** | any office-bearing line | **The inflation factor is per-office variable** — 1.76× for `ccb52f4c`, 16.1× for `c2ab6637` (FINDING-2) — so one threshold means a different number of mails for every office. `park.py:170-172` states the mechanism verbatim: the line "fires on EVERY delivery … it shows the retry-churn being absorbed". A line count measures SendGrid retry churn, not client harm. **RETAINED as the S1.1 sensitivity comparator** (it is the unit every measurement in §D1.5 is stated in, and it is complete). |
| **U-2** | distinct correlation id (`message_id` and/or `lead_id`) alone | **Neither field is uniform (FINDING-3).** Six of the top-25 offices have 0 distinct `message_id`; eight have 0 distinct `lead_id`. A distinct-id unit gives those offices `arrivals = 0` — never eligible for the zero floor, and a **zero denominator** for the rate floor. It hides exactly the offices whose traffic is all bookings-and-refusals. |
| **U-4** | a new office-bearing `mail_arrived` line emitted at intake, then counted | **Non-retroactive.** The 09-04..09-12 replay could not run on it, which destroys §2(ii)'s free historical positive control (the identical reasoning that rejected pythia's G5 and N4). **NAMED as the wave-2 cure with an owner** (§12) — U-3's fallback branch exists only because the substrate lacks a uniform mail identity, and that is a substrate defect, not a permanent condition. |
| **U-5** | `booking_attempt` joined to an office | **Office-blind at the line.** `book_appointment.py:224` verbatim: *"`office_phone_hash` on `booking_attempt` above is a correlation token, not an identity"*; `witness_cadence_deadman.tf:95-98`: *"this counts BOOKING-STAGE ARRIVALS (office-blind), NOT pipeline termini."* Joining through `office_phone_hash` would also import a phone-derived key into S-1 against charge §10. |

### D1.4 The inflation-factor proof S1.1 must produce (discharges the co-occurrence UV-P by measurement as well as by source)

FINDING-2 discharges the co-occurrence question from source. S1.1 must still **quantify** it,
because the *factor* is what calibrates A and r, and the factor is per-office.

**Required output (not a pinned query string — see the UV-P below):** for each office in each
window, S1.1 publishes `lines`, `mails` (= `count_distinct(message_id)`), per-event line counts,
and the derived `inflation = lines / (A_id + A_noid)`. Plus the direct co-occurrence count: the
number of `message_id` values that carry **both** `terminal_decline` and `terminal_decline_parked`
in the window. If that count is > 0, a naive sum of the two events over-counts by exactly that many
mails, and the receipt states the per-office over-count.

```
[UV-P: CloudWatch Logs Insights supports a second `stats` command chained after a first (needed for the count_distinct(event)-by-message_id then count()-by-kinds co-occurrence shape) | METHOD: run the two-stage query once, read-only, at S1.1 and record status+recordsScanned | REASON: not probed by this seat; if unsupported the builder computes the fold in the evaluator/analysis from a single `stats count() by chiropractor_guid, event, message_id` pass, which is equivalent and costs the same scanned bytes (V-14)]
```

### D1.5 RULED parameters — the two floors

```
ZERO FLOOR  (page class: FLOOR-ZERO)
    arrivals(office, W) >= A   AND   bookings(office, W) == 0
    W = 3 days rolling        A  = 5                                  [R-150, kept]

RATE FLOOR  (page class: FLOOR-RATE)          <-- the PRIMARY class; the founding case
    arrivals(office, W) >= A'  AND   bookings(office, W) >= 1
                               AND   bookings/arrivals < r
    W = 3 days rolling        A' = 20         r = 0.025  (2.5%)
```

**The two classes are DISJOINT by construction** (`bookings == 0` vs `bookings >= 1`). No office can
appear in both; no double-page; each has its own probe at S1.4 per R-160.

**The calibration arithmetic, from the measured tables (all rates stated in U-1, the complete unit):**

| office (guid8) | 8d lines / bookings / rate | 3d-B lines / bookings / rate | 3d-C lines / bookings / rate |
|---|---|---|---|
| **`ccb52f4c`** | 580 / 4 / **0.69 %** | 344 / 4 / **1.16 %** | 112 / 1 / **0.89 %** |
| `933a026c` (nearest quiet) | 27 / 1 / 3.70 % | 17 / 1 / 5.88 % | 12 / 4 / 33.3 % |
| `7a1e83fd` (nearest ≥7 %) | 58 / 4 / 6.90 % | 40 / 4 / 10.0 % | 6 / 2 / 33.3 % |
| `79be1b75` | 14 / 1 / 7.14 % | 14 / 1 / 7.14 % | 9 / 0 / — (ZERO class) |
| every other booking office | — | — | 8.7 % … 57 % |

*Separation band under U-1:* `ccb52f4c` ≤ **1.16 %** in its worst window; the nearest office that
must stay quiet is **3.70 %**. The geometric midpoint is 2.07 %.

*Why r = 2.5 % and not 2.0 %.* The U-1 → U-3 transform **shrinks arrivals**, so every office's rate
**rises**. That is safe for the quiet side and dangerous for the fire side. For `ccb52f4c` to still
fire in window B, the de-dup factor `f` must satisfy `4f/344 < r`:

| r | max tolerable f, window B | headroom over the measured 8-day f = **1.65** |
|---|---|---|
| 0.020 | 1.72 | **×1.04 — 4 % headroom. Too thin: a false-quiet on the founding office.** |
| **0.025** | **2.15** | **×1.30 — 30 % headroom** |
| 0.030 | 2.58 | ×1.56, but the quiet-side margin to 3.70 % falls to ×1.23 |

r = 0.025 keeps **≥ ×1.30 on the fire side in the worst window** and **×1.48 on the quiet side**
(3.70 / 2.5), and the quiet-side margin can only improve under U-3. r = 0.02 buys a marginally
better quiet side at the cost of a 4 %-headroom fire side — the wrong trade for an instrument whose
founding failure is a missed page.

*Why A' = 20.* At r = 0.025 an office needs `arrivals > 1/0.025 = 40` to fire with a single
booking, so **A' is mathematically dominated by r today** — it is a guard against a future r
increase and a statistical-confidence floor, not the operative lever. A' = 20 is set below the
implied 40 so it never becomes the reason the founding office is missed. (At A' = 50 the window-C
cell under U-3 becomes fragile; at A' = 30 the 8-day cell for `933a026c` flips in and out
depending on unit. A' = 20 is stable across every measured cell.)

*Why A = 5 is kept unchanged.* It is R-150-ruled and under U-3 it finally denominates in **mails**,
which is the unit it was written against. Changing it is a VALUE fork; this ADR does not take it.

### D1.6 RULED: the S1.1 sensitivity table — specification

S1.1 publishes **one** table before any build begins. Cells = the **firing office-set and its size**.

- **Windows (3):** `A` = 8 d 09-04..09-12 (the founding window) · `B` = 3 d 09-09..09-12 ·
  `C` = 3 d 09-11..09-14.
- **Units (2):** **U-3** (ruled) and **U-1** (comparator).
- **Floors (2) × thresholds:** ZERO at A ∈ {5} · RATE at (A', r) ∈ {20, 30, 50} × {0.020, 0.025, 0.030, 0.050}.
- **Per-office columns, every row, every window:** `guid8` · `office_name` · `lines` · `mails` ·
  `arrivals(U-3)` · `arrivals(U-1)` · `bookings(P1)` · `bookings(P2)` · `bookings(P3)` · `rate(U-3)` ·
  `rate(U-1)` · `inflation` · `offer_class` · `floor_class`.
- **Per-query columns:** `status` · `recordsScanned` · `bytesScanned` · `estimatedRecordsSkipped` ·
  `logGroupsScanned` (the UNTAKEN-ZERO fence: a zero without a comparable `recordsScanned` is not a
  finding).
- Also required (F6 discipline carried): the office-set **with no smoke-lead exclusion** and with
  **each candidate exclusion**, side by side. `ccb52f4c` must fire under **every** variant.

### D1.7 RULED: the calibration criterion (S1.1's exit gate)

| # | Criterion | On failure |
|---|---|---|
| **K1** | `ccb52f4c` fires the **RATE** floor under the ruled `(U-3, A'=20, r=0.025)` in **all three windows** | **RECEDE to the operator.** S1.1 does NOT raise r or lower A'. Re-ruling a threshold is a VALUE fork. Publish the table and stop. |
| **K2** | Every office whose U-3 booking rate is **≥ 7 %** is quiet under **both** floors in all three windows | RECEDE. A quiet-side breach means the unit or r is wrong, not the office. |
| **K3** | The ZERO floor's firing set is **fully enumerated and class-labelled** in each window, and every member is (a) a genuine zero-booking office, (b) a known-dark office, or (c) the attribution residual — **no unexplained member** | Investigate the unexplained member before build; it is a finding about the log plane, not noise. |
| **K4** | `933a026c` (the 3.70 % office) is quiet in all three windows **and the receipt states why**. It **cannot** fire, and the proof is closed-form: it has 1 booking over **at most** 27 arrivals in the 8-day window (27 = its total line count, the ceiling U-3 can reach), so its U-3 rate is **≥ 3.70 % > r = 2.5 %** whatever the de-dup factor turns out to be. Secondarily, its distinct `message_id` is 0, so `A_id = 0` and its U-3 arrivals are the non-`message_id` terminal-outcome lines only (≥ 7 visible: one `booking_completed` + six `booking_gate_declined`) — plausibly below A' = 20 as well. The receipt states which of the two kept it quiet. | If it fires, RECEDE — do not adjust the data or the threshold in the seat. |
| **K5** | `recordsScanned` reported for every query and comparable to the control | The zero is not a finding (charge §10 UNTAKEN-ZERO). |

**What happens to the `***` residual and the known-dark offices** is ruled in **D5**, not here:
`***` is **not an office** and is removed from floor evaluation entirely; known-dark offices are
**labelled, never suppressed**.

---

## D2 — F3 + F11 · DEADMAN AND DEGRADED-RUN POSTURE

All module facts below are `[VERIFIED]` reads of
`a8 origin/main (2b7c00d):terraform/modules/stacks/lambda-freshness-deadman/{variables.tf,main.tf}`.

### D2.1 RULED: **C4 + L4** — prober **and** success-gap, with a fail-closed in-run control

Three alarms carry the evaluator's own silence, plus two that the scheduled-Lambda module gives for
free, plus one in-run refusal that is code (not a metric) and therefore live from deploy:

| # | Signal | Resource | Answers | Live from |
|---|---|---|---|---|
| 1 | **stopped being invoked** | `lambda-freshness-deadman` v1.4.1 `mode="prober"` → alarm `autom8-ebi-booking-floor-lambda-freshness` (`main.tf:349-395`) | "the schedule died / the rule was disabled" | **apply** (see D2.3) |
| 2 | **the watcher died** | `prober_self_deadman` → `autom8-ebi-booking-floor-freshness-prober-liveness` (`main.tf:412-435`, `treat_missing_data="breaching"`, period 86400, evaluation_periods 2) | "the prober itself stopped" | apply |
| 3 | **invoked but crashing** | `service-lambda-scheduled` v1.0.2 `${name}-lambda-errors` (`main.tf:164-175`, metric `AWS/Lambda Errors`, `error_rate_threshold` default 1, 5 min) — created iff `alarm_actions` non-empty | "it runs and throws" | **apply** (native metric, no soak) |
| 3b | **work stranded** | `${name}-dlq-not-empty` (`main.tf:193-203`) | "the retry path is accumulating" | apply |
| 4 | **runs, does not crash, but its read is untrustworthy** | **L3 in-run control → `FLOOR-REFUSED` SNS publish + withheld success metric** (code) | "the query returned nothing / partial / mis-scoped" | **apply** |
| 5 | **runs, does not crash, and never produces a trustworthy verdict** | `enable_invoke_success_gap_alarm = true` → `autom8-ebi-booking-floor-invoke-success-gap` (`main.tf:467-488`, `treat_missing_data="breaching"`, statistic `SampleCount`) | "no controlled run has completed for 2 h" | **S1.7**, after the ≥ 7 d soak of `LastSuccessTimestamp` (charge §3) |

**The answer to charge §4's standing question** (*"F3 decides whether S-1 ships two-sided-complete
at deploy or with a named 7-day hole"*): **two-sided-complete at deploy on the liveness axis, with
ONE named and bounded deepening at S1.7.** Signals 1, 2, 3, 3b and 4 are all live at apply. The
residual between S1.5 and S1.7 is precisely: *the evaluator runs, does not error, does not DLQ, and
its own in-run control wrongly passes* — which signal 5 closes. That residual is NAMED, it is not
discovered later, and it is not the whole "runs but never succeeds" class (signal 4 covers every
failure the evaluator can detect about itself).

### D2.2 Rejected alternatives

| # | Option | REJECTED because |
|---|---|---|
| **C1 + L1** | prober only, fail-open | Pythia's own words name the hole: *"C1 pages on silence, never on wrongness — an evaluator that runs on time and returns an empty result forever is GREEN under C1."* Under the D3 hourly cadence EventBridge keeps `Invocations` non-zero **whatever the query does**, so the prober is green through a total failure of the only thing S-1 exists to do. Fail-open is the epoch's founding defect relocated one level up: a green light over an unread substrate. |
| **C5 + L3** | success-gap only, no prober, plus refusal | The success-gap's input is a **service-emitted** metric and is therefore governed by charge §3 — it cannot arm until a ≥ 7 d soak is receipted. Choosing it *alone* means S-1 ships at S1.5 with **no** silence deadman at all, which is a direct refusal of charge §2(iii) (*"it is not a follow-up"*). The prober's input is the target's native `AWS/Lambda Invocations` and has datapoints from apply-time (D2.3), so it is the only day-one liveness signal available. |
| **C2** | heartbeat mode + a second Insights read | `mode = "heartbeat"` is a DECLARED seam **rejected by a second validation block** — `variables.tf:66` `condition = var.mode == "prober"`. Selecting it fails `terraform plan`. It is therefore a bespoke build, and it regresses: the second reader needs its own runtime, which needs its own deadman. |
| **C3** | raw `AWS/Lambda Invocations` floor alarm | Its failure signal is absence, so it must run `treat_missing_data = "breaching"` — pages on any metric-delivery hiccup, and cannot distinguish "ran and errored" from "ran and succeeded" without an `Errors` companion. It is the pattern the module was built to replace. |
| **L2** | fail-closed on `status == "Complete"` only | A *Complete* query over an empty or mis-scoped window returns a clean, confident, wrong "nobody is below the floor". Status alone does not see the `recordsScanned ≈ 0` case, which is exactly the UNTAKEN-ZERO class the charge fences. |

### D2.3 The inverted premise, corrected — and the premise that IS now verified

- **CORRECTED (S-2 confirmed).** `freshness_treat_missing_data = "missing"` does **not** mean the
  prober's own death fires the freshness alarm. `variables.tf:173` verbatim: *"Default \"missing\"
  (v1.4.0): a MISSING gauge does NOT page."* `main.tf:361` verbatim: *"a dead prober is caught by
  the separate prober self-dead-man, not by this alarm."* The watcher-of-the-watcher is resource
  #2 above. **Any S1.7 receipt designed against the inverted mechanism tests the wrong alarm** —
  see D2.6.
- **DISCHARGED (packet UV-P NEW-2, previously INHERITED-not-re-derived).** *"A prober-published
  gauge has datapoints from apply-time, so the §3 caveat does not postpone this deadman"* is now
  **VERIFIED**: `main.tf:321-335` declares `resource "aws_lambda_invocation" "prober_seed"` whose
  comment reads verbatim: *"Invoke the prober ONCE at apply so a real datapoint exists within
  seconds and the alarm settles to a true state immediately -- closing the race with no
  false-breach on the empty window AND no false-quiet."* The freshness alarm is armed and true from
  apply. This UV-P is removed from the register.
- **INHERITED module residual, carried verbatim into the risk map and NOT curable this wave**
  (`main.tf:406-411`): *"a prober that is invoked-but-erroring ticks Invocations yet publishes
  nothing -- neither this alarm (Invocations > 0) nor the freshness alarm (MISSING is `missing`)
  catches that."* Mitigation actually present here: signal #3 (`${name}-lambda-errors`) covers the
  *evaluator's* error case; the *prober's* error case remains the module's accepted residual.

### D2.4 RULED: exact module parameters

**Instance 1 — liveness (prober + freshness + self-deadman).** Created iff
`enabled && length(alarm_actions) > 0 && mode == "prober"` (`main.tf:97`).

```hcl
module "office_floor_freshness" {
  source = "git::https://github.com/autom8y/a8.git//terraform/modules/stacks/lambda-freshness-deadman?ref=v1.4.1"

  name                      = "autom8-ebi-booking-floor"          # 24 chars -- see D2.5
  function_name             = module.office_floor.lambda_function_name   # never hand-typed
  declared_cadence_seconds  = 3600        # variables.tf:21 ; = the D3 cadence
  buffer_multiplier         = 2           # variables.tf:31 (default) -> threshold 7200s
  check_schedule_expression = "rate(5 minutes)"   # variables.tf:42-45
  environment               = var.environment
  enabled                   = true
  mode                      = "prober"    # variables.tf:53-66 ; heartbeat fails plan
  alarm_actions             = [data.terraform_remote_state.shared.outputs.platform_alerts_topic_arn]
  # left at module defaults, stated so they are chosen and not inherited by accident:
  #   freshness_alarm_period_seconds = null -> derived clamp(3600) = 3600   (main.tf:90-91)
  #   freshness_evaluation_periods   = 3    (variables.tf:150-153)
  #   freshness_datapoints_to_alarm  = 2    (variables.tf:161-164)  -> 2-of-3
  #   freshness_treat_missing_data   = "missing" (variables.tf:172-175)
  #   lookback_days                  = 60   -> effective 60d >> (2+1)*3600s ; main.tf:381 precondition satisfied
}
```

`check_schedule_expression = "rate(5 minutes)"` is **not** a default and is load-bearing:
`variables.tf:43` verbatim — *"For a sub-hourly target … set this <= the freshness alarm period so
each evaluation period has a fresh datapoint -- the 2-of-3 M-of-N needs at least ~2 published points
inside the 3-period window to fire."* At a 3600 s alarm period, `rate(5 minutes)` puts ~12 prober
reads per period, decoupling M-of-N counting from prober phase (the identical rationale the
precedent block records at `autom8y:terraform/services/email-booking-intake/contente_booking_reconcile.tf`).

**Instance 2 — trustworthy-verdict (success-gap ONLY). NOT created at S1.5. Created at S1.7.**

```hcl
module "office_floor_success_gap" {
  source = "git::https://github.com/autom8y/a8.git//terraform/modules/stacks/lambda-freshness-deadman?ref=v1.4.1"

  name                            = "autom8-ebi-booking-floor"
  function_name                   = module.office_floor.lambda_function_name   # required var; unused when enabled=false
  declared_cadence_seconds        = 3600      # required var; unused when enabled=false
  environment                     = var.environment
  enabled                         = false     # -> local.create=false : NO prober, NO rule, NO freshness alarm, NO self-deadman
  enable_invoke_success_gap_alarm = true      # local.create_success_gap is INDEPENDENT of enabled/mode (main.tf:106-111)
  success_metric_namespace        = "Autom8y/EbiOfficeFloor"   # variables.tf:238-241
  success_metric_name             = "LastSuccessTimestamp"     # variables.tf:244-247 (default)
  success_metric_dimensions       = {}                         # variables.tf:250-253 (default, no dimensions)
  success_max_gap_seconds         = 7200                       # = 2 x cadence ; variables.tf:256-270
  alarm_actions                   = [data.terraform_remote_state.shared.outputs.platform_alerts_topic_arn]
}
```

Derived (`main.tf:119-124`): `success_gap_period = min(7200, 86400) = 7200`;
`success_gap_evaluation_periods = ceil(7200/7200) = 1`. Alarm name
`autom8-ebi-booking-floor-invoke-success-gap`, `LessThanThreshold(1)` on `SampleCount`,
`treat_missing_data = "breaching"`.

**⚠ ARMING ORDER — and the structural reason a scratch topic is NOT the mechanism.** The module
exposes **one** `alarm_actions` list shared by the freshness alarm, the self-deadman **and** the
success-gap alarm; there is no per-alarm action variable. It is therefore impossible, within one
module instance, to point the success-gap at a scratch topic while the freshness alarm pages
`platform_alerts`. Two shapes exist; **this ADR rules the second**:

1. *(rejected)* one instance, success-gap on from S1.5, actions on a scratch SNS topic through the
   soak, repointed at S1.7. **REJECTED:** it would also demote the freshness alarm and the
   self-deadman to the scratch topic for the whole soak — arming the liveness deadman into a void
   is exactly telos Law 2's defect, and it breaks charge §2(iii) at deploy.
2. **RULED:** two instances. Instance 1 lands at **S1.5** with `alarm_actions = [platform_alerts]`.
   The evaluator emits `LastSuccessTimestamp` **from S1.5** (metric soaks). Instance 2 — the alarm —
   is **created at S1.7** with `alarm_actions = [platform_alerts]`, after the ≥ 7 d daily-sum soak
   is receipted in the handoff. This is charge §3 read literally: *the metric soaks, then the alarm
   arms*. No scratch topic, no repoint, no self-inflicted page at apply (which
   `treat_missing_data="breaching"` would otherwise guarantee: `main.tf:454-458` records an
   empirical receipt of an alarm on an empty `LastSuccessTimestamp` reaching ALARM in ~2 min).

### D2.5 The 64-char IAM trap

The module derives `prober_function_name = "${name}-freshness-prober"` (`main.tf:51`) and then
suffixes it `-schedule` (EventBridge rule, `main.tf:282`) and `-role` (IAM role, `main.tf:145`),
both AWS-capped at 64. Scar precedent: commit `77746170` *"shorten contente reconcile Lambda name to
fit IAM role 64-char limit"*.

| derived name | length |
|---|---|
| `autom8-ebi-booking-floor` (the module's `name`) | 24 |
| `autom8-ebi-booking-floor-freshness-prober` (Lambda) | 42 |
| `autom8-ebi-booking-floor-freshness-prober-schedule` (rule) | **51 ✓** |
| `autom8-ebi-booking-floor-freshness-prober-role` (IAM role) | 46 ✓ |

**Never pass the target function's own name.** The evaluator Lambda is
`autom8-email-booking-intake-office-floor` (40) — `+ "-freshness-prober-schedule"` would be 66 and
**overflow**. The short `autom8-ebi-…` form is mandatory, mirroring the precedent.

### D2.6 RULED: the in-run control (L3) and the refusal class

```
control PASSES  iff   query_status == "Complete"
                AND   records_scanned  >= 500
                AND   offices_with_bookings >= 5
```

Measured baselines that set the floors (all three windows, this morning's replay):
`recordsScanned` = 61,981 (8 d) / 20,276 (3 d B) / **7,010 (3 d C)**; `offices_with_bookings` =
33 / 33 / **22**. The floors sit at ≈ 7 % and ≈ 23 % of the *smallest observed* value — conservative
enough never to fire on a genuinely quiet holiday window, sharp enough that a wrong log group, a
wrong epoch window, a truncated result or a mis-scoped filter cannot pass.

`offices_with_bookings >= 5` is the *discriminating* half: a mis-scoped or empty query cannot
manufacture five offices with booking termini. `records_scanned >= 500` alone would pass a query
that scanned the right bytes and matched nothing.

**On control FAILURE the run REFUSES** (telos Law 4 — *never blank: a refusal names its kind*):

| | behaviour |
|---|---|
| page class | **`FLOOR-REFUSED`** — a distinct class from `FLOOR-ZERO` / `FLOOR-RATE`, with its own runbook row and its own probe at S1.4 |
| page content | the kind: `query_status`, `records_scanned`, `offices_with_bookings`, `control_reason`, the window, and the literal sentence *"no floor verdict was produced for this run"* |
| verdict | **no floor verdict is published.** A quiet verdict from a degraded read is never emitted. |
| success metric | **`LastSuccessTimestamp` is WITHHELD.** This is the wire between L3 and signal #5: two consecutive refusals (2 h at the D3 cadence) turn the alarm plane red without any human reading a page. |
| publish gate | the SNS refusal publishes only on the `hour == 11` run (D8); the withheld metric carries the off-hours case to the alarm plane, which is the correct channel for it under R-154 (business-hours consumer) |

### D2.7 RULED: the S1.7 two-sided proof — three legs, none resting on the inverted premise

> The forbidden design is *"kill the prober and watch the freshness alarm fire"*. That is the
> inverted premise (D2.3) and it tests the wrong resource: a MISSING gauge is treated `missing` and
> **does not page**.

**Leg 1 — evaluator liveness (SUBJECT-LIVE, the freshness alarm).**
Disable the **evaluator's** EventBridge rule (`module.office_floor.schedule_rule_name`) for a
bounded, announced window. The prober keeps running and publishes a **rising**
`Autom8y/Freshness age_since_last_invocation_seconds` gauge. After threshold 7200 s plus 2 breaching
periods of 3600 s, `autom8-ebi-booking-floor-lambda-freshness` goes **OK → ALARM** (≈ 4 h; D3).
**Observe the SNS delivery on `platform_alerts`, not merely the alarm state.**
Re-enable the rule → next invocation → gauge drops → **ALARM → OK** via `ok_actions`.
Both poles required; the restore leg is not optional.
*Negative pole across the soak:* with the evaluator running normally the alarm sits in **OK with
datapoints present** — not `INSUFFICIENT_DATA`. This is the exact discrimination
`ebi-booking-liveness-dark` failed (charge §3).

**Leg 2 — watcher-of-the-watcher (`prober_self_deadman`), split PROBE / SUBJECT and labelled.**
Its geometry is period 86400 × 2 evaluation periods, so a live outage proof costs ≥ 48 h. S1.7
therefore produces **two** receipts, each labelled for what it proves:
- *(configuration, SUBJECT)* `aws cloudwatch describe-alarms --alarm-names autom8-ebi-booking-floor-freshness-prober-liveness`
  showing `TreatMissingData=breaching`, `Period=86400`, `EvaluationPeriods=2`, `Threshold=1`,
  `ComparisonOperator=LessThanThreshold`, `ActionsEnabled=true`, actions = the `platform_alerts` ARN.
- *(action path, **PROBE — explicitly not the subject**)* `aws cloudwatch set-alarm-state
  --state-value ALARM` on that alarm, and observe the delivery on `platform_alerts`, then
  `--state-value OK`. The handoff must say, in words, that this proves the **action path** and not
  the **detection path**, per charge §2 (*"a control proves the PROBE ran. It cannot prove the
  SUBJECT runs"*).

**Leg 3 — trustworthy verdict (the success-gap, S1.7+, SUBJECT-LIVE on the real mechanism).**
Force the in-run control to FAIL for one bounded window (the honest lever: point the evaluator's
window at a deliberately empty interval via its `FLOOR_WINDOW_OVERRIDE` env for two runs — a
deliberately-broken **input** the live surface correctly refuses, never a defect injected into
working code, per `discriminating-canary-doctrine`). The refusal path emits **no**
`LastSuccessTimestamp` by construction → after `success_max_gap_seconds = 7200` / 1 period,
`autom8-ebi-booking-floor-invoke-success-gap` goes **ALARM** and delivers to `platform_alerts`.
Remove the override → the next controlled run emits → **OK**. Two-sided, on the real metric, real
alarm, real channel.

---

## D3 — F2 · CADENCE

### D3.1 RULED: **hourly evaluation, page only on the 11:00Z run** (`rate(1 hour)`; page gate `hour == 11` UTC)

`declared_cadence_seconds = 3600` follows from this and is the input to D2's geometry.

### D3.2 The blind-window arithmetic, from the module's own thresholds

```
blind window = freshness_threshold  +  datapoints_to_alarm x alarm_period   ( + <= prober interval )
             = (cadence x buffer)   +  2 x clamp(cadence)
```
(`main.tf:64` `freshness_threshold_seconds = declared_cadence_seconds * buffer_multiplier`;
`main.tf:90-91` `derived_alarm_period = min(86400, max(60, floor(cadence/60)*60))`;
`variables.tf:150-164` 2-of-3 default.)

| option | cadence | threshold | alarm period | accumulation | **blind window** |
|---|---|---|---|---|---|
| **RULED — hourly** | 3600 | 7200 s = 2 h | 3600 s | 2 × 3600 = 2 h | **≈ 4.1 h** (+ ≤ 5 min prober interval) |
| daily + `freshness_alarm_period_seconds = 3600` | 86400 | 172800 s = 48 h | 3600 s | 2 h | ≈ 50 h |
| daily, module defaults | 86400 | 48 h | 86400 s | 48 h | **≈ 96 h** |

**The daily-default option is disqualifying on its own terms:** a 96 h blind window on an instrument
whose measurement window is 72 h means the evaluator can be dead for **longer than the period it
measures** — the arc's organizing defect reproduced inside the cure.

### D3.3 Rejected alternatives

| # | Option | REJECTED because |
|---|---|---|
| **B1** | daily at ~11:00Z, module defaults | 96 h blind window > the instrument's own 72 h window (above). Its stated advantage — *"one run = one verdict, so the replay and the live run are the same call"* — is **illusory**: under the ruled shape the replay and the live run execute the **same pinned query constant** (D8.3) and differ only in the publish gate, so B1 buys nothing there. |
| **B4** | daily + `freshness_alarm_period_seconds = 3600` | Cuts the blind window to ~50 h, still **within 40 % of the instrument's own window**, and still leaves the §2(ii) control with **one** evaluation per day — a single datapoint from which "the subject runs" cannot be distinguished from "the subject ran once". Cost of the alternative is $0.24/yr. |
| **B3** | twice daily | Halves the latency and leaves the blind window at ~48 h; strictly dominated by hourly at the same page volume (the page gate, not the cadence, controls page volume). |

### D3.4 How the §2(ii) SUBJECT-LIVE control counts evaluations vs pages

Pythia's own named hazard: *"'evaluated' and 'paged' become different events … conflating them
would produce a green receipt for a silent instrument."* The receipt therefore carries **two
columns that are never summed**:

| column | source | expected | what a failure means |
|---|---|---|---|
| **evaluations/day** | `count()` of `office_floor_evaluated` lines | **24** (accept ≥ 22 on a deploy day) | the evaluator is not running — leg 1's subject |
| **controlled evaluations/day** | those with `control_status="PASS"` | ≥ 22 | the evaluator runs but its read is untrustworthy — D2.6's subject |
| **pages/day** | `count()` where `paged=true` | **0 or 1** (never > 1 — D8) | > 1 means the page gate leaked; 0 with offices below the floor means the publish path is dead |
| **page class distribution** | `page_class ∈ {digest, refused, none}` | — | a `refused` run is a first-class outcome, not a gap in the series |

The soak table in the handoff prints all four per day for ≥ 7 days. **`pages/day` may legitimately
be 0 for the whole soak** — that is why §2(i)'s two-sided probe at S1.4 must exercise the **page
path** specifically, per class (R-160: `FLOOR-ZERO`, `FLOOR-RATE`, and `FLOOR-REFUSED`).

---

## D4 — F1 · EVALUATOR HOME

### D4.1 RULED: **A1 — a dedicated Lambda inside `autom8y:services/email-booking-intake/`**

Its own function (never a second entrypoint), built from the EBI image via
`service-lambda-scheduled?ref=v1.0.2` — the pattern already resident in the stack at
`terraform/services/email-booking-intake/contente_booking_reconcile.tf:58` and
`forwarding_nudge.tf:39` `[VERIFIED at autom8y a1f3ecf3]`.

Proposed names: Lambda `autom8-email-booking-intake-office-floor` (40 chars); deadman module `name`
`autom8-ebi-booking-floor` (D2.5).

### D4.2 Rejected alternatives, with reasons carried

| # | Option | REJECTED / passed over because |
|---|---|---|
| **A2** | separate small service, own stack, own state, own deploy | Its isolation argument is real but buys less than it costs here. The wave's single irreversible node is one EBI apply either way; a second stack adds new remote-state wiring for the page topic, a **second deploy path nobody has exercised**, and a second terraform state to lock — against a wave with one rite-disjoint critic. Decisively: A2 does **not** reduce the instrument count — its evaluator needs the *same* deadman module, so the isolation is of blast radius only, and the blast radius it isolates (an EBI apply removing the watcher) is covered by the watcher's own alarms being in the *same* apply, which is what makes them fail **loudly together** rather than the watcher silently surviving a half-applied stack. Kept on the record as the strongest opposing option. |
| **A3** | Insights **scheduled query**, no Lambda | *"A3 cannot satisfy R-154 or §2(iii). Destinations are S3 + lookup-table ONLY (V-12) — no SNS, no metric, no alarm… Its own-deadman surface is `get-scheduled-query-history`, a **pull** API with no signal to alarm on. Net surface is larger than A1… A3 is available and insufficient, not unavailable."* |
| **A4** | second scheduled entrypoint on an existing EBI Lambda | *"A4 is a trap and is REJECTED. … the S-1 evaluator could die and the deadman would stay green. That is §2(iii) defeated by construction — silence wearing a green light, inside the instrument built to end that."* |
| **A0** | an operator-run query, no runtime | Refused in one sentence rather than left silent: it fails R-150's "live", has no consumer path, and cannot carry a deadman — the instrument would be the operator's memory, which is the state the epoch exists to leave. |

### D4.3 Blast-radius consequence — stated, accepted, and fenced

A `services/**` merge fires an **untargeted whole-stack `terraform apply -auto-approve`** on EBI
(**R-136, ACCEPTED**). `[INHERITED — V-30/SVR-B; MUST be re-verified at the merge instant, not
inherited from this ADR.]` Therefore, binding on S1.5:

1. **The merge IS the apply.** The pending-terraform set must be **enumerated at the merge instant**
   (not at authoring) and cleared or consciously accepted, item by item, in the handoff.
2. **Deploy singleton** — one deploy at a time; a `waiting` `workflow_dispatch` holds the main
   concurrency slot and cancels every push plan.
3. **Re-verify `pin == served` at the merge instant**: `aws lambda get-alias --function-name
   autom8-email-booking-intake --name live --query FunctionVersion` then `get-function --qualifier
   "$V" --query Code.ImageUri` (charge §10; WRONG-OBJECT fence — unqualified reads `$LATEST`).
4. **NEVER a Service Terraform manual apply on a pinned stack** (image-pin rollback, risk row 11).
5. **Roll-forward only (R-80); disarm = delete.**
6. S1.5 is the **only irreversible node** of this wave.

### D4.4 ⚠ CORRECTION — the new IAM is **four** grants, not two

The packet and pythia's V-21 state the delta as `logs:StartQuery` + `logs:GetQueryResults`. That is
the delta for *reading*; the evaluator also *pages* and *emits a success metric*. The evaluator is a
**new** Lambda with its **own** role (created by `service-lambda-scheduled`), so it starts from zero:

| action | resource / condition | why |
|---|---|---|
| `logs:StartQuery` | the EBI log group ARN | run the pinned query |
| `logs:GetQueryResults` | `*` (the API takes a queryId, not an ARN) | read it back |
| `sns:Publish` | **exactly** the `platform_alerts` topic ARN | the page (D8) |
| `cloudwatch:PutMetricData` | `*` with `Condition: {StringEquals: {"cloudwatch:namespace": "Autom8y/EbiOfficeFloor"}}` | `LastSuccessTimestamp` (D2.4 instance 2); `PutMetricData` has no resource ARN but **does** honour the namespace condition key — the same scoping the deadman module itself uses at `main.tf:203-210` |

`[VERIFIED]` `emit_success_timestamp` (the `autom8y-telemetry` helper the module's
`success_metric_name` default is named for, `variables.tf:245-246`) is **absent from the EBI
service**: `git grep -rn 'emit_success_timestamp' origin/main -- services/email-booking-intake`
returns nothing at `a1f3ecf3`. The evaluator therefore publishes the datapoint itself via
`put_metric_data`, **without dimensions**, to match the module's `success_metric_dimensions = {}`
default — a dimensioned datapoint would not be seen by the alarm.

**Wiring:** author the grant as a named `aws_iam_policy` in the EBI stack and pass it through
`service-lambda-scheduled`'s declared escape hatch `additional_iam_policies` (list of policy ARNs,
`variables.tf:189-192`), so the grant is an auditable object rather than an inline blob.
`alarm_actions = [platform_alerts_topic_arn]` must also be passed to the scheduled module — without
it, `${name}-lambda-errors` is **not created at all** (`main.tf:165` `count = var.error_rate_threshold > 0 && length(var.alarm_actions) > 0 ? 1 : 0`), which would silently drop D2 signal #3.

---

## D5 — F5 · CLASS ANNOTATION MECHANISM, THE `***` RESIDUAL, AND DARK OFFICES

### D5.1 RULED: **E2 — a dated static snapshot, with the snapshot's age rendered on the page**

Source: `READ-offer-activity-sizing-2026-09-11` (live Asana read at asana `6430cec5`, Company-ID
prefix join per `ADR-ws-join-office-naming-path-2026-09-08` Option C, 4,193 Offers, 898 prefixes,
0 collisions). `[INHERITED — charge §7]`

**Shape:** a build-time constant `guid_prefix → max_offer_activity` baked into the evaluator image
(a checked-in data file, not a runtime fetch), carrying `snapshot_date = 2026-09-11`.

**Rendering rules (all three binding):**
1. Every page prints `snapshot: offer-class snapshot <snapshot_date> (age <N> d)`.
2. A guid absent from the snapshot renders **`class=unknown`** — never blank, never inferred, never
   suppressed (telos Law 4).
3. Past **30 days** of snapshot age the class renders `class=<value> (STALE <N>d)` on every row.
   This converts E2's named failure — *substantive staleness that is silent* — into a
   **page-visible state**, which is the only form of staleness a reader can act on. The date alone
   is a footnote; the STALE marker is an instrument.

### D5.2 Rejected alternatives

| # | Option | REJECTED because |
|---|---|---|
| **E3** | live Asana read at page time | *"E3 puts Asana in the page path, and charge §11 records 9 `AsanaServiceUnavailableError` at exactly the 12:20Z/13:00Z instants: the page would inherit Asana's outages."* Choosing E2 additionally makes the whole cadence question **instant-agnostic** (coupling 2) — one ruling removes a scheduling constraint from D3. |
| **E1** | the SSM census `served_set` / `allowlist` | **WRONG-OBJECT.** It is the *contente_booking monolith-served* discriminator, not the Asana Offer-grain `max_offer_activity`, and `production.tfvars` itself stamps it *"⚠ census dated"*. Two different objects answering two different questions. |
| **E4** | derive dark/live from the plane's own long-window booking history | **A proxy, not the class.** `15caa02c` books while dark at the Offer grain (charge §7), so the two provably disagree — and this morning's measurement confirms it books (P1=1, P2=6 over 8 d) while its single Offer sits `INACTIVE`. |
| **E5** | no class; name the office and let the operator look it up | Fails R-150 as ruled. Kept on the record as the strongest opposing option: *a page that says only "office `ccb52f4c`: 352 arrivals, 4 bookings, 1.14 %" is never wrong.* D5.1 rule 3 is the answer to it — E2 with a legible age is never *silently* wrong, which is the property E5 was protecting. |

### D5.3 RULED: the `***` attribution residual is **NOT an office**

Measured: `***` carries **144 / 127 / 15** office-bearing lines across the three windows, **0
bookings**, 0 distinct `lead_id`, 30 distinct `message_id` (8 d). Under a zero floor at A = 5 it
**fires in all three windows** — and firing it as an office is a **category error**: it is the
bucket of lines whose office guid is absent or unresolvable, i.e. an aggregate over an unknown
number of offices, not one client.

**Ruling:**
- `***` is **excluded from floor evaluation** (it can satisfy neither floor, because neither
  "arrivals for this office" nor "bookings for this office" is defined for it).
- It is **never suppressed.** Every page carries a final line:
  `ATTRIBUTION RESIDUAL (not an office): lines=<n> mails=<m> — <p>% of window lines`.
- If the residual share exceeds **10 %** of window lines the page adds
  `residual share HIGH — office attribution is degrading`. (Measured today: 144/1,725 = **8.3 %**
  over 8 d, 127/1,129 = **11.2 %** over window B, 15/402 = **3.7 %** over window C — so this
  tripwire is live at today's rates and will speak on its first page. That is intended: it is the
  same class as the R-158 tail's 54/202 `kind=absent` residual and it should be visible, not
  discovered later.)
- **UV-P:** the exact composition of `***` (guid absent at the line vs guid present but
  unresolvable to a name) is not characterised. S1.1 must split it. See §11.

### D5.4 RULED: known-dark and disabled offices are **LABELLED, never SUPPRESSED**

R-150's own words: *the page carries the Offer-grain class **so a dark office's silence reads as
expected, not as a defect***. That is an instruction to **label**, not to filter. And the epoch's
founding law is that hiding a real zero is the defect being cured. Therefore:

- The disabled office `40f86e73` (17 / 14 / 3 lines; 0 bookings; fires the zero floor under U-1 in
  windows A and B) and the malformed-guid office `e5a68603` (12 / 9 / 3 lines; fires in A and B)
  are **evaluated, printed, and class-labelled** like every other office.
- They are **sectioned** (D8.1) so the reader's eye lands on the actionable set first and their
  silence reads as expected.
- Under the **ruled** unit U-3 both are likely to fall below A = 5 on their own arithmetic
  (`40f86e73` has 0 distinct `message_id` and ~4 non-`message_id` terminal lines over 8 d) — which
  is the honest way for them to go quiet: **by the unit, not by a suppression list.**
- A guid with no resolvable `office_name` renders as a **guid-prefix-only row** (`<guid8> —`), never
  a crash and never a drop. This is the 50-guids-vs-49-names case (V-15) made structural.

**Explicitly rejected:** gating the firing population on the SSM census (`D2`/`D3` in the packet's
F5a) — *"a newly-onboarded office is structurally invisible to the floor; the instrument would be
blind exactly where onboarding failures live."* Population = **every office with arrivals in W**
(D1 = pythia's D1, R-150 literal, no list).

**Snapshot refresh — a DEFER with an owner, never `NO WATCHER`.** See §12 row 1: owner = the S-1
consumer (the operator) via the incident-commander runbook row; trigger = the refutable predicate
*"`snapshot_age_days > 30` appears on any page"*, which the page itself emits (D5.1 rule 3); watcher
= the page. The defer is self-surfacing by construction.

---

## D6 — F7 · SCAN SCOPE

### D6.1 RULED: **G1 — no narrowing.** Carried from pythia with the baseline made explicit.

Measured `[VERIFIED — V-13/V-14 + this morning's replay]`: a 3-day Insights scan of
`/aws/lambda/autom8-email-booking-intake` = **20,276 records / 5,412,087 B**, `estimatedRecordsSkipped
0`, `logGroupsScanned 1`; an identical window **with** a `filter` scanned the **identical** bytes —
**Insights bills SCANNED, not MATCHED.** A `filter` buys exactly zero cost reduction.

Replay-observed spread across three windows: 61,981 (8 d) / 20,276 (3 d) / 7,010 (3 d) records —
≈ 7,750 records/day.

**Cost at the ruled hourly cadence** [rate is **UV-P**, published us-east-1 $0.005/GB scanned]:
5.41 MB × 24 × 365 ≈ **47 GB/yr ≈ $0.24/yr**. The conclusion survives a 100× error in the rate.

### D6.2 The baseline to watch, and its watcher

| item | value at authoring | trigger | owner/watcher |
|---|---|---|---|
| `/aws/lambda/autom8-email-booking-intake` stored bytes | **82,410,556 B** at 90-day retention (V-17) | **`> 10 GB / 90 d`** (a refutable predicate, ~121× today) | §12 row 4 — the named lever is **G2**, a field-index policy on `chiropractor_guid` / `office_name` (`put-index-policy`; none exists today, V-16). G2 is the **only** lever that can move `estimatedBytesSkipped` off zero. |

"No narrowing" and "no tripwire" are different rulings; this ADR makes both explicit so the cost
curve has an owner rather than a silence.

### D6.3 Rejected alternatives

| # | Option | REJECTED because |
|---|---|---|
| **G3** | narrow the window | Unavailable — W = 3 days is RULED (R-150). |
| **G4** | log-stream prefix narrowing | *"Lambda log streams are keyed by version/instance, not by office — a prefix selects a deploy generation, never an office subset. It cannot express the scope S-1 needs."* |
| **G5** | emit compact lines to a dedicated log group and scan that | *"REJECT for wave 1: new log group + new writer in the hot path + a non-retroactive substrate — the 09-04..09-11 replay could not run on it, which destroys §2(ii)'s free historical positive control."* (The identical reason U-4 is deferred in D1.3.) |

---

## D7 — F12 · PAGE-REPEAT POLICY — **MECHANISM ONLY. THE POLICY IS THE OPERATOR'S.**

This ADR does **not** choose. It states, for each policy the operator may pick, exactly what state
and what lookback it costs and whether it is buildable in wave 1 **without a prior-state store**.
`ccb52f4c` has been below the floor for 8 days; the difference between these policies is between
1 page and 8.

| # | Policy | State required | Lookback required | Buildable in wave 1? | Cost / note |
|---|---|---|---|---|---|
| **M1** | page every run while the condition holds; one digest | **none** | W = 3 d (unchanged) | **YES** | Zero delta from the D8 shape. The condition IS ongoing harm; the risk is reader fatigue, which is F4's question at the consumer end. |
| **M2** | page on **transition only** (first crossing) | **a prior-state store** (DynamoDB table / S3 object / SSM parameter) + its IAM + its own failure mode (a lost store = a permanently silent instrument) | W = 3 d | **NO — not without a new persistence resource.** That store is precisely WS-2's substrate, which sitting X deferred (R-155/R-156; the lifecycle engine is dark). Building it inside WS-1 is either good reuse or scope the sitting did not charge — an operator call, not a builder call. | A missed or ignored first page is **never repeated** — a silent failure mode inside an instrument built to end silent failure. |
| **M3** | page every run; the digest carries a **state-free "day N below floor"** counter | **none** | **W + N_max** days. For N_max = 14 the scan is 17 d ≈ 132k records ≈ 35 MB/run (from the measured 7,750 rec/day). Mechanism: one Insights pass with `bin(1d)` per-office daily counts; the evaluator folds them into N trailing rolling W-day windows **in memory**. | **YES** | Hourly cost ≈ 307 GB/yr ≈ **$1.53/yr** at the UV-P rate — still negligible (D6). Digest grows by one column. |
| **M4** | M3 + repeats past N days route to a **second, lower-urgency channel** | none beyond M3 | as M3 | **Buildable, but** the second channel has **no confirmed reader** (the F4 question), and every channel must be proven two-sided and soaked. It adds a page class to S1.4's probe matrix. | Preserves attention on new crossings while keeping standing ones visible. |

**Coupling the operator should hold when answering:** the consumer word (F4) is being given against
a page volume. *"Will you act within one business day?"* has a different answer for one page per
incident than for a daily standing page. The D8 shape below is policy-agnostic: M1, M3 and M4 all
render inside it; only M2 changes the build.

---

## D8 — THE PAGE SHAPE AND THE PER-RUN LOG LINE

### D8.1 RULED: **at most ONE SNS publish per UTC day**, a digest, never one publish per office

- The publish gate is `hour == 11` UTC (D3). All other runs evaluate, log, and stay silent.
- Exactly one of two mutually exclusive classes is published on that run:
  **`FLOOR-DIGEST`** (control PASSED) or **`FLOOR-REFUSED`** (control FAILED, D2.6). Never both.
- **Never one publish per office.** One publish naming every office over either floor. Per-office
  publishing is available only on an explicit operator word, because it changes S1.4's probe target
  and the consumer's page volume simultaneously.

**Digest body — sectioned by CLASS first, floor second.** The reader's attention is the scarce
resource; class-first ordering is what makes a dark office's silence *read as expected* (R-150)
without suppressing it (D5.4).

```
subject: [ebi-floor] <n> offices below floor | W=3d | <date>

run     : window=<startZ>..<endZ> (3d) | unit=U-3 | offices_evaluated=<m>
control : PASS | query_status=Complete | records_scanned=<n> | offices_with_bookings=<n>
          evaluations_since_last_page=<n>
snapshot: offer-class snapshot 2026-09-11 (age <N>d)[ STALE]

[1] ACTIONABLE  (class=active | activating)
    RATE  ccb52f4c  <office_name>   arrivals=352  bookings=4  rate=1.14%   class=active
    ZERO  <guid8>   <office_name>   arrivals=<n>  bookings=0             class=active
[2] EXPECTED SILENCE  (class=inactive | dark)
    ZERO  <guid8>   <office_name>   arrivals=<n>  bookings=0             class=inactive
[3] CLASS UNKNOWN
    ZERO  <guid8>   —                arrivals=<n>  bookings=0             class=unknown
[4] ATTRIBUTION RESIDUAL (not an office; never suppressed)
    unattributed: lines=<n> mails=<m> (<p>% of window lines)
```

- `office_name` in full **on the plane and on the page** (R-154, allowed); **guid8 only in every
  `.ledge` artifact**. **No phone digits on any face** (charge §10; S-1 must not widen the
  `office_phone`-in-`stage_exception` exposure, risk row 12).
- Within a section, rows sort **RATE before ZERO**, then by `arrivals` descending.
- A zero-length section prints its header with `(none)` — never a blank page and never an absent
  section (telos Law 4).

### D8.2 RULED: the per-run log lines

**One per run** — `office_floor_evaluated`:
`window_start` · `window_end` · `window_days` · `arrival_unit` · `query_status` ·
`records_scanned` · `bytes_scanned` · `offices_evaluated` · `offices_with_bookings` ·
`control_status` · `control_reason` · `zero_floor_count` · `rate_floor_count` ·
`residual_lines` · `residual_share` · `paged` (bool) · `page_class` (`digest|refused|none`) ·
`snapshot_date` · `snapshot_age_days` · `evaluator_version`.

**One per evaluated office per run** — `office_floor_office`:
`chiropractor_guid` · `office_name` · `arrivals` · `bookings` · `booking_rate` ·
`floor_class` (`zero|rate|quiet`) · `offer_class` · `offer_class_snapshot_date` · `lines` ·
`mails` · `inflation`.

**Binding field-shape rule (S-9, the silent-miss class):** these fields are **FLATTENED**
(`**office_log_fields(ctx)` form), **never nested under `office=`**. `handler.py` and
`book_contente.py` emit the nested form and an Insights query keyed on `chiropractor_guid`
**silently misses those lines**. S-1's own emission must not reproduce the defect it reads through.

### D8.3 RULED: the replay and the control are the **same query shape** — by construction

The arrival/booking query is a **single pinned constant** in the evaluator module, parameterised
**only** by `(log_group, start_epoch, end_epoch)`.

- **S1.1's replay** is that constant with the three historical windows substituted.
- **The live evaluation** is that constant with the rolling window substituted.
- **The §2(ii) control** reads `office_floor_evaluated` / `office_floor_office` to count
  evaluations vs pages (D3.4) — a *different* query over the *same* log group, whose job is to
  witness that the pinned constant ran.
- The handoff **prints the constant once, verbatim**, and both the S1.1 receipt and the soak
  receipt cite that one text. A divergence between "the query the replay ran" and "the query the
  instrument runs" is then impossible by construction rather than by review.

---

## §10 CONSOLIDATED BUILDER CONTRACT — THE RECEIPT EACH RULING MUST PRODUCE

Every receipt is a **falsifiable artifact with its own-hands command and unpiped rc**, per charge §9.
"The code does it" is not a receipt.

| # | Ruling | Receipt the builder must produce | Node |
|---|---|---|---|
| **D1** | arrival unit U-3 + two floors (A=5 · A'=20 · r=0.025) | The **sensitivity table** of D1.6 in full (3 windows × 2 units × 12 floor settings, per-office and per-query columns) + the **inflation-factor / co-occurrence** output of D1.4 + an explicit PASS/FAIL line against **K1–K5**. Published **before** any build begins. | S1.1 |
| **D2** | C4 + L4 (prober + success-gap + fail-closed in-run control) | (a) `terraform plan` output showing both module instances with the parameters of D2.4 verbatim; (b) `aws cloudwatch describe-alarms` for all five alarm names showing `ActionsEnabled`, actions = the `platform_alerts` ARN, `TreatMissingData`, `Period`, `EvaluationPeriods`, `Threshold`; (c) the **three-leg two-sided proof** of D2.7 with the SNS delivery observed on each firing leg **and** each restore leg; (d) the ≥ 7 d **daily-sum soak table** for `Autom8y/EbiOfficeFloor LastSuccessTimestamp` **before** instance 2 is created. | S1.3 / S1.5 / S1.6 / S1.7 |
| **D3** | hourly evaluate, page at `hour == 11`Z | The four-column **evaluations-vs-pages table** of D3.4, per day, for ≥ 7 days, with `evaluations/day`, `controlled evaluations/day`, `pages/day`, `page_class` distribution **never summed into one number**. Plus the blind-window arithmetic of D3.2 re-derived from `describe-alarms` output (threshold, period, datapoints_to_alarm), not from this ADR. | S1.6 |
| **D4** | A1, dedicated Lambda in `services/email-booking-intake/` | (a) the **pending-terraform set enumerated at the merge instant** (not at authoring), item by item, each cleared or consciously accepted; (b) `pin == served` re-verified at the merge instant via `get-alias` then `get-function --qualifier`; (c) the deploy-singleton receipt (no concurrent run held the slot); (d) the **four** IAM actions of D4.4 shown in the applied policy document, with the `cloudwatch:namespace` condition present. | S1.5 |
| **D5** | E2 dated snapshot + STALE marker; `***` excluded-but-printed; dark labelled | (a) a rendered example page for each of the four sections **including a zero-length section** printing `(none)`; (b) a rendered page with a guid that has **no resolvable name** (guid-prefix-only row) proving no crash and no drop; (c) the residual-share line with the measured value; (d) a rendered page with `snapshot_age_days > 30` proving the STALE marker appears. | S1.3 / S1.4 |
| **D6** | G1, no narrowing; 10 GB/90 d ceiling with a watcher | `recordsScanned` / `bytesScanned` / `estimatedRecordsSkipped` / `logGroupsScanned` carried on **every** query in every receipt (UNTAKEN-ZERO), plus the current `describe-log-groups` stored-bytes figure recorded as the baseline in the defer registry. | S1.1 / S1.6 |
| **D7** | mechanism only — no policy chosen | The handoff records **which policy the operator chose** and, if M2, that a new persistence resource entered the wave's scope **as an operator decision**, with its own blast-radius row. If no word is given, the build ships M1 and the handoff says so **as a named default, not as a ruling**. | S1.2 |
| **D8** | one digest publish per UTC day; flattened log lines; one pinned query constant | (a) the **pinned query constant printed verbatim once** in the handoff, cited by both the S1.1 receipt and the soak receipt; (b) an Insights query keyed on `chiropractor_guid` returning the evaluator's **own** `office_floor_office` lines — which proves the flattening (a nested emission returns zero, the S-9 silent-miss, and that zero is the two-sided proof); (c) the S1.4 probe run **per page class** (`FLOOR-ZERO`, `FLOOR-RATE`, `FLOOR-REFUSED`), two-sided each, on a scratch topic. | S1.3 / S1.4 |

---

## §11 UV-P REGISTER — frozen syntax, carried verbatim into the handoff, each with an owner

```
[UV-P: CloudWatch Logs Insights supports a second `stats` command chained after a first | METHOD: run the two-stage co-occurrence query once, read-only, at S1.1 and record status + recordsScanned | REASON: not probed by this seat; if unsupported the equivalent single-pass `stats count() by chiropractor_guid, event, message_id` fold in the evaluator is exact and costs identical scanned bytes (V-14)]

[UV-P: the de-duplication factor f = lines / (A_id + A_noid) for office ccb52f4c over the 3-day window 09-09..09-12 is below 2.15, which is what the ruled r = 0.025 requires for K1 to hold in that window | METHOD: the S1.1 sensitivity table computes f per office per window directly | REASON: only the 8-day f (1.65) is measured; the 3-day factor is unmeasured and is the single arithmetic on which the ruled r depends. If f >= 2.15 in window B, S1.1 RECEDES to the operator per K1 and does NOT raise r]

[UV-P: the composition of the `***` attribution residual - whether the office guid is ABSENT at the line or PRESENT-but-unresolvable to a name | METHOD: split the residual at S1.1 by ispresent(chiropractor_guid) and report both counts per window | REASON: not broken out by this morning's replay; the ruling (D5.3, excluded from evaluation but never suppressed) is correct under either composition, but the runbook action differs]

[UV-P: the founding count "406 inbound mails, 2 completed bookings, eight days" is reproducible from the EBI log plane under some predicate | METHOD: none available; the three predicates measured over the identical 8 days give 580 lines / 329 distinct message_id / ~352 terminal-outcome mails and 4 booking_completed | REASON: the charge does not record the predicate. A = 5 was calibrated against an unrecoverable unit; the thresholds in D1.5 are therefore calibrated against measured quantities and the founding figure is carried as provenance, not as an input]

[UV-P: the test-lead / smoke-lead contact-information convention exists as a practice | METHOD: operator word at the S0b sitting, or the F6-4 reserved non-production guid cure | REASON: VERIFIED-ABSENT in code at origin/main across both repos (V-24/V-25). The replay runs with NO exclusion plus the sensitivity variants of D1.6; the live instrument runs with a known, uncharacterised false-positive channel until the convention is codified or struck]

[UV-P: a human acts on a platform_alerts page within one business day | METHOD: operator word inscribed with its instant at S1.2, or measured acknowledgement | REASON: unfalsifiable before the word. The CHANNEL is VERIFIED to reach a human (2 confirmed subscribers: a Slack-relay Lambda and one confirmed email endpoint) but has never fired. Charge §6 is explicit: absent the word, S-1 is built and NOT armed, REFUSED-CORRECTLY]

[UV-P: the EBI deploy path at the merge instant is still an untargeted whole-stack terraform apply -auto-approve with pin == served | METHOD: re-read .github/workflows/service-deploy-dispatch.yml + service-deploy-lambda.yml at origin/main AND get-alias/get-function --qualifier, AT the merge instant | REASON: INHERITED from V-30/SVR-B, true at authoring; R-136 blast radius and the image-pin rollback hazard both key on it, and it must never be inherited from a document]

[UV-P: the post-#121 emitted V2-MISSING string routes to the DIVERGENCE twin, not HALT | METHOD: read the monolith emitter at base.py ~:711 | REASON: the legacy repo is outside this seat's directories (charge UV-P-2); never exercised in 45 d of Sum 0.0. Not a WS-1 blocker; carried for WS-0]
```

**DISCHARGED by this ADR** (removed from the register, with the receipt):
- *"`terminal_decline_parked` co-occurs with `terminal_decline` for one mail"* → **VERIFIED TRUE**
  from `autom8y a1f3ecf3:services/email-booking-intake/src/email_booking_intake/park.py` (FINDING-2).
- *"a prober-published gauge has datapoints from apply-time"* → **VERIFIED TRUE** via
  `aws_lambda_invocation "prober_seed"`, `a8 2b7c00d:…/lambda-freshness-deadman/main.tf:321-335` (D2.3).
- *"a uniform correlation field exists on office-bearing lines"* → **VERIFIED FALSE** by measurement
  (FINDING-3); this is why U-2 is rejected.
- *"`treat_missing_data=\"missing\"` means the prober's own death fires the freshness alarm"* →
  **VERIFIED FALSE** (D2.3); the S1.7 receipt is designed against the corrected mechanism.

---

## §12 DEFER REGISTRY — `owner · trigger · watcher`; every trigger a refutable predicate

| # | Defer | Owner | Trigger (refutable) | Watcher |
|---|---|---|---|---|
| 1 | Refresh the Offer-class snapshot (D5.1) | the S-1 consumer (operator), via the S1.2 runbook row | **`snapshot_age_days > 30` printed on any page** | **the page itself** (D5.1 rule 3) — self-surfacing |
| 2 | **U-4**: emit a uniform office-bearing `mail_arrived` line at intake, retiring U-3's fallback branch (D1.3) | WS-1 successor seat | **the S1.1 table shows `A_noid / arrivals > 0.25` for any office in any window** (i.e. a quarter of that office's arrivals rest on the fallback) | S1.1's own table; re-checked at each soak week |
| 3 | Characterise the `***` residual and cure the attribution gap (D5.3) | WS-1 successor seat | **`residual_share > 10 %` printed on any page** (live at today's rates: 11.2 % in window B) | the page itself |
| 4 | **G2** field-index policy if scan volume grows (D6.2) | the S-1 owner | **`/aws/lambda/autom8-email-booking-intake` stored bytes > 10 GB / 90 d** (82.4 MB today) | quarterly `describe-log-groups`; recorded in the handoff with today's baseline |
| 5 | The module's accepted residual: an **invoked-but-erroring prober** publishes nothing and is caught by neither the self-deadman nor the freshness alarm (`main.tf:406-411`) | a8 module owner | **a prober error appears in `/aws/lambda/autom8-ebi-booking-floor-freshness-prober` logs while both alarms read OK** | the a8 module's own backlog; NOT curable in this wave |
| 6 | Codify or strike the smoke-lead convention (F6-1 / F6-4) | operator | **the operator's word at S0b, or the first `FLOOR-ZERO` page traced to a smoke burst** | the page |
| 7 | WS-2 build (the #439/#441 consumer) | operator (sequencing fork, held) | **the T5 recon's re-derivation of V-29** | the T5 recon artifact |
| 8 | Orphaned Calendly IaC home (V-7) and V-33 (the post-#121 emitter) | operator → monolith owner | **any apply touching `/ecs/monolith-prod` metric filters**, or the halt alarm changing state after 45 d of Sum 0.0 | WS-0's closure amendment |

No row above is `NO WATCHER`. Rows 1, 3 and 4 have **the instrument itself** as the watcher, which
is the only defer shape this epoch should accept.

---

## §13 WHAT THIS ADR DOES **NOT** RULE

Held by the operator; this ADR is written so that none of the eight rulings above is invalidated by
any answer to these four:

1. **The consumer word** (F4 / charge §6). Absent it, S-1 is **built, soaked, proven two-sided, and
   NOT armed** — REFUSED-CORRECTLY, with the blocker named. D2's arming order (instance 2 created at
   S1.7) is compatible with an indefinite hold: nothing arms into a void.
2. **The page-repeat policy** (F12 / D7). Mechanism stated for all four; the choice is the
   operator's, and the D8 shape renders M1, M3 and M4 unchanged.
3. **The smoke-lead practice** (F6). The replay runs with **no exclusion plus every candidate
   variant** (D1.6) precisely so that this answer cannot change the S1.1 verdict.
4. **WS-2 sequencing** (F9). Untouched; T5 remains read-only recon.

Also not this wave, per charge §1: **R2** (the clause-(d) observer), **R3** (coverage), **R4** (the
dark column). And not this ADR: any change to R-150's `W = 3 days` or `A = 5`, or to R-154's
consumer — those are ratified and the rulings above are built inside them.

---

## §14 EVIDENCE GRADE AND ANTI-THEATER SELF-CHECK

**Grade: MODERATE** — single seat, no rite-disjoint corroboration (`self-ref-evidence-grade-rule`).
Every terraform/code claim is a command-cited read at a named `origin/main` ref
(`autom8y-asana 49506a21` · `autom8y a1f3ecf3` · `a8 2b7c00d`); every quantitative claim is from
this morning's read-only replay with its window stated; everything else is labelled INHERITED or
carried as UV-P in §11.

| check (`option-enumeration-discipline` · `anti-theater-checks`) | result |
|---|---|
| Every ruling enumerates before it rules, and every rejection names a reason? | Yes — D1 (5 units, 3 booking predicates), D2 (5 rejected), D3 (3 rejected), D4 (4 rejected), D5 (4 rejected), D6 (3 rejected), D8 (1 rejected shape). D7 rules nothing by design. |
| ≥ 1 no-new-mechanism option in each slate? | D1 U-1 · D2 C1+L1 · D3 B1 · D4 A0 · D5 E5 · D6 G1 (which is the ruling) · D7 M1 |
| Does the ADR merely ratify the packet's RECs? | **No.** It **overturns** the packet/pythia REC on D1 (U-3, not N1), D2 (C4+L4, not C1) and D3's framing; it **corrects** the packet's stale `autom8y` ref, the IAM delta (four grants, not two), and the scratch-topic arming order (structurally impossible in one module instance); it **discharges** three UV-Ps by direct read and **falsifies** one premise by measurement. |
| Is any ruling's headline claim checked against its own discipline? | Yes, and one was caught: the first draft's K4 asserted `933a026c` is excluded by `A' = 20` on an arrival estimate this seat cannot compute. Replaced with the closed-form proof (1 booking / ≤ 27 arrivals ⇒ rate ≥ 3.70 % > r) that holds whatever the unit resolves to. |
| Does a ruling rest on a number this seat did not measure? | **One, and it is named:** the 3-day de-dup factor for `ccb52f4c` in window B (§11, UV-P 2). It is the binding arithmetic for r = 0.025, it is bounded (the measured 8-day factor is 1.65 against a 2.15 ceiling), and its failure path is **RECEDE to the operator**, not a threshold re-tune in the seat. |
| Fences honoured | STALE-TREE (three refs named; the packet's stale `autom8y` ref corrected) · no reads under `.knossos/worktrees/` or `.terraform/` · no phone digits · no raw client names, guid8 only · every AWS fact from a `describe`/`get`/`list` or from the read-only replay · **no commits, no applies, no mutations, one file written** |

**The acid test.** *Will this look obviously right in 18 months?* The one place it might not: U-3's
fallback branch (`A_noid`) exists only because the log plane has no uniform mail identity. If U-4
lands (defer §12 row 2), the fallback becomes dead code and the unit collapses to
`count_distinct(mail_id)` — which is what it should have been from the start. This ADR is written so
that day is a **deletion**, not a re-design: the unit's definition, the thresholds, the page shape
and every alarm survive it unchanged.
