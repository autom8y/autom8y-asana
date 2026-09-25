---
type: review
artifact_kind: runbook
initiative: read-the-name
sprint: S1.2
rite: sre
station: incident-commander
created: 2026-09-14
revised: 2026-09-14   # rev 2 — six change-warden conditions C-1..C-6 applied
decision_space_of_record: .ledge/decisions/RATIFICATION-decision-space-sitting-XI-2026-09-14.md
implementation_adr: .ledge/decisions/ADR-read-the-name-s1-implementation-2026-09-14.md
upstream_observation: .ledge/reviews/OBS-read-the-name-s1-2026-09-14.md   # PR #448, branch sre/s1-1-observe-20260914T040422
offer_class_snapshot: .ledge/reviews/SNAPSHOT-offer-class-2026-09-11.json   # PR #449, branch docs/e2-offer-class-snapshot-2026-09-14
charge: .sos/wip/CHARGE-read-the-name-s1-per-office-floor-2026-09-11.md
critique: change-warden (dre), CERTIFIED-WITH-CONDITIONS, 2026-09-14 — C-1..C-6 applied in rev 2
consumer_state: WITHHELD
consumer_state_instant: 2026-09-14 (sitting XI, S0b, R-168)
evidence_grade: MODERATE   # self-ref ceiling; the runbook's subject is an instrument that has not yet run
status: accepted
arming_state: RECORD-ONLY — this runbook arms nothing; every page path named here is on a scratch topic.
---

# RUNBOOK — read-the-name S-1 · the per-office booking floor

> **Read this line first.** The instrument this runbook governs **has no reader**. The operator
> withheld the consumer word at sitting XI (R-168, 2026-09-14). Every page path — digest, prober
> freshness, success-gap — is pointed at a **scratch topic**. Nothing in §1 is on duty. §1 is the
> contract the reader inherits **on the word**, written now so that the word costs one terraform
> change and not a design.

**Revision 2 (2026-09-14)** applies six conditions from change-warden's rite-disjoint certification.
One of them, **C-1, inverted this runbook's central axis**: the Offer-grain class is no longer a
router and must never suppress action. See §1.0.1 for the correction and why the first version was
wrong.

## §0 METHOD, REFS, FENCES

**Authorities, in precedence order.** `RATIFICATION-decision-space-sitting-XI-2026-09-14.md`
(the decision space of record; R-160 · R-167 · R-168 · R-169 · R-171 · R-172) →
`ADR-read-the-name-s1-implementation-2026-09-14.md` (D1–D8, the delegated implementation rulings) →
`CHARGE-read-the-name-s1-per-office-floor-2026-09-11.md` §6 (superseded on its consumer clause, see
§2.0) → `OBS-read-the-name-s1-2026-09-14.md` (S1.1, the measured substrate: K1–K5 all PASS).
**A sprint artifact may not narrow a ruling from a higher tier** — the rule that C-3 enforces below.

**Governance reads were taken from a named ref.** Sitting XI is present at `origin/main` and absent
from this repo's working tree; the S1.1 artifact is present only at
`origin/sre/s1-1-observe-20260914T040422`; the E2 snapshot is on `origin/docs/e2-offer-class-snapshot-2026-09-14`
(PR #449). All were read with `git show "${REF}:path"`, never from a checkout. (Scar:
`worktree-vs-session-repo-path-trap`, five instances, one of them a false governance fork put to the
operator.)

**Fences honoured in this artifact.** guid8 only; no office names; no phone digits on any face
(charge §10, risk row 12); no page path repointed; nothing merged, nothing armed.

**What this runbook is NOT.** It is not an arming authority, not a threshold re-tuning (ADR D1.7:
on K1/K2 failure the seat recedes to the operator — K1/K2 passed, nothing was tuned), and not a
claim that S-1 is live. S-1 is **built-pending, unarmed, unread**. change-warden's certification is
explicit that it *"is not an activation GO and confers no arming authority."*

---

## §1 THE PAGE CLASSES × THE OFFICE CLASSES

### §1.0 The two axes, named

**Page class** — what the instrument concluded (R-160 gives two floors; ADR D2.6 gives the refusal;
ADR D2.4/D2.7 give two distinct deadmen, which are a different kind of page and are separated here
because they name the *instrument*, never an office):

| page class | emitted by | means |
|---|---|---|
| `FLOOR-ZERO` | the 11:00Z digest, section-placed | arrivals ≥ A = 5 and **bookings = 0** in the 3-day window |
| `FLOOR-RATE` | the 11:00Z digest, section-placed | arrivals ≥ A′ = 20, bookings ≥ 1, and rate < r = 2.5 % |
| `FLOOR-REFUSED` | its own SNS publish, mutually exclusive with the digest | the evaluator's **own in-run control failed** — no floor verdict was produced for this run |
| `DEADMAN-liveness` | `autom8-ebi-booking-floor-lambda-freshness` (prober) | the **evaluator stopped running** (≈ 4 h detection at the D3 cadence) |
| `DEADMAN-success-gap` | `autom8-ebi-booking-floor-invoke-success-gap` | the evaluator runs but has produced **no trustworthy verdict** for ≥ 7200 s (two consecutive refusals) |

**Office class** — the Offer-grain annotation from the E2 dated snapshot (ADR D5.1), printed on
every row with its age and a `STALE` marker past 30 days. The landing snapshot (#449) carries the
vocabulary `{active 13 · inactive 13 · ignored 2 · activating 1}`, plus the two classes the
evaluator derives rather than reads:

| office class | source | meaning |
|---|---|---|
| `active` | snapshot row | a live Offer at the Offer grain |
| `activating` | snapshot row | onboarding in flight |
| `dark-at-Offer-grain` (`inactive`) | snapshot row | no live Offer |
| `ignored` | snapshot row | a **prospect**, not a served client — 2 offices, including `933a026c` (S1.1's nearest-quiet-office RATE control, K4) |
| `unknown` | **no snapshot row** for this guid — never blank, never inferred (D5.1 rule 2) | post-snapshot onboarding, or a guid the sizing read never saw |
| `***` attribution residual | not an office at all (D5.3) | an aggregate over an unknown number of offices |

### §1.0.1 ⚠ THE CORRECTION THAT REV 2 EXISTS FOR — class is CONTEXT, never a SUPPRESSOR

**Rev 1 of this runbook routed reader attention by office class, and that was wrong.** It sent
`dark-at-Offer-grain` rows to EXPECTED SILENCE with the instruction *"no action is owed."*
change-warden joined S1.1's fully-enumerated 12-member window-A `FLOOR-ZERO` firing set against the
landing snapshot and found the defect:

| S1.1 shape | guid8 | E2 class | bookings in the sizing read | rev 1 routed it to |
|---|---|---|---|---|
| **(a) TRUE STALL** | `87bd31d7` | **`inactive`** | **15** | **[2] EXPECTED SILENCE — "no action is owed"** |
| **(a) TRUE STALL** | `6b93fb76` | **`inactive`** | **10** | **[2] EXPECTED SILENCE — "no action is owed"** |

**Both of the instrument's two true positives would have been silenced by their own class label.**
That is the founding defect recurring *inside* the instrument built to cure it. A misrouted
no-action row costs the reader attention; a false-silenced stall costs a client. They do not trade.

**THE RULING, applied to every floor cell below.** The routing key is **not** the class. It is the
per-office **`last_booking_age_days`** — a 30-day plane-derived booking lookback the evaluator
carries on every row (change-warden is adding it to S1.3):

```
ACTIONABLE        <=>  the office hit a floor AND last_booking_age_days <= 30
                       (it books; it stopped; that is a stall — WHATEVER its class)
EXPECTED SILENCE  <=>  the office hit a floor AND last_booking_age_days > 30 (or never)
                       AND its class is dark-at-Offer-grain or ignored
```

**The class is printed beside the row as context and never decides the routing.** It tells the
reader *what kind of thing this office is*; `last_booking_age_days` tells them *whether it is
breaking*. This is now **N=3 measured class-vs-booking disagreements** (`87bd31d7`, `6b93fb76`, and
`15caa02c` — which the sizing read itself flags as *"resolved fine, classified dark … Reported, not
adjudicated"*, the same disagreement ADR D5.2 already cites as its reason for rejecting E4). Three
measurements agreeing is not an anomaly; it is the class axis telling us what it is not for.

`[UV-P: the evaluator emits a per-office last_booking_age_days field from a 30-day booking lookback | METHOD: deferred-to-S1.3-build | REASON: the field does not exist at S1.2; change-warden routed it into the S1.3 build after certifying this runbook — SVR AP-4, design-choice masquerading as platform-behavior]`

**A build consequence S1.3 must not discover late.** ADR D8.1 sections the digest with the literal
predicate `[1] ACTIONABLE (class=active | activating)`. Under this correction that predicate is
**wrong**: section membership keys on `last_booking_age_days ≤ 30`, not on class. D8.1's *shape*
(four sections, class-first ordering, `(none)` for empty) stands; its *section predicate* is
superseded. Filed as **DW-10**.

**The general lesson, stated so it survives this wave.** The class axis was introduced to make a
dark office's silence read as expected (R-150). It does that. It was then quietly promoted to
deciding who gets read — and an annotation that was never validated as a routing key became one.
Every remaining use of class in this runbook is a label printed next to a decision, never the
decision.

### §1.1 The grid — a named human action per cell

Read `WITHIN ONE BUSINESS DAY` as the R-154 business-hours contract: a page landing Friday evening
waits until Monday, accepted on the record.

**The owner, for every floor cell below (C-5).** The action owner is **the operator (Tom Tenuta)**,
per R-154 (*"the human who acts is the operator"*) and R-168 (the word is his to give), **until the
role is re-seated on the record**. Where a cell says "route to the platform owner" or "the
onboarding owner", those are the operator's onward routes, not a second reader — the page has one
addressee.

**The locator, for every floor cell below (C-5).** The page carries guid8 only, so every
investigation starts from the same two named things, never from a reconstruction:

- **log group** `/aws/lambda/autom8-email-booking-intake`
- **query** `Q-S1`, the single pinned Insights constant ruled by ADR D8.3, parameterised **only** by
  `(log_group, start_epoch, end_epoch)` and printed verbatim once at `OBS-read-the-name-s1-2026-09-14.md`
  §2. The evaluator pins this exact text, so *the query the replay ran* and *the query the
  instrument runs* cannot diverge. Paste it, set the window, add `| filter office_guid = "<full guid>"`.

The guid8 → office → owner lookup is **not yet a named path** and is filed as **DW-9** with an
owner. Until DW-9 closes, a reader who needs to reach an office's owner asks the operator.

#### `FLOOR-ZERO` × office class

Routing key: `last_booking_age_days`. Class is printed context.

| office class | disposition | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| **active** | **ACTIONABLE — highest urgency on this floor** | Run the §4.2 fragility check first (this floor flips on ±1 arrival, and `783b40aa` — one synthetic arrival from firing — is `active` in the snapshot). If it survives: open `/aws/lambda/autom8-email-booking-intake` with `Q-S1` over the page's window filtered to this guid, and answer *did mail arrive and produce no booking, or did the booking path fault?* The discriminating events are `booking_intake_fault` and `booking_gate_declined` against `terminal_decline`. Route the mechanism half to the platform owner; for the client half, see DW-9. | The office books again, **or** the operator has decided this office is not expected to book and the class is corrected in the next snapshot. A page that stops because the window rolled is **not** resolved. | **Never contact a client from the page.** The page names an *office*, not a patient, and carries no patient identity. Never phone from it (no phone digits are on the page by construction; do not go find them). Never silence the office by adding it to a list — D5.4 forbids suppression lists; if it should be quiet, fix the **class**, not the filter. |
| **activating** | **ACTIONABLE — but a different question** | Ask *has this office ever booked?*, not *why did it stop?* This is an onboarding-completion question: the funnel head may never have been wired. Same locator; look for the **absence** of any booking event across the full 30-day lookback. Route to the onboarding owner. | Either a first booking lands, or the onboarding gap is named and ticketed with an owner. | Do not treat it as a regression. Do not conclude "the instrument is wrong" — an activating office with arrivals and zero bookings is exactly the class the charter says is structurally invisible today. |
| **dark-at-Offer-grain**, `last_booking_age_days ≤ 30` | **ACTIONABLE — a class contradiction, and it is the founding shape** | **This is `87bd31d7` and `6b93fb76`.** The office books and stopped; its `inactive` label is a *second* finding, not a reason to stand down. Work it exactly as the `active` cell (same locator, same discrimination), **and** raise the class disagreement so the snapshot can be corrected. | As the `active` cell, **plus** the class is adjudicated — corrected, or recorded as a known disagreement (N=3 and counting). | **Do not read the class and stop.** That is the exact instruction rev 1 gave and it would have silenced both of this instrument's true positives. Do not wait for rising arrivals: `87bd31d7` fell 33 → 12 across windows A and B while stalling. |
| **dark-at-Offer-grain**, `last_booking_age_days > 30` or never | **EXPECTED SILENCE** | Read the section header and stop. No action is owed. This is the genuine dark set — in window A: `e63bbbe0`, `8a9b1a84`, `40f86e73`, `ea98e732`, `5a19f1ad`, `e5a68603`, `cf6ae0f2`, `2b591e43`, `2786b72d`, `735416d5`. | Nothing to resolve. The row is doing its job by being visible-and-labelled. | Do not chase it. Do not ask for it to be filtered — it is printed on purpose (D5.4: hiding a real zero is the defect being cured). Do not read its presence as instrument noise. |
| **ignored** (prospect) | **EXPECTED SILENCE** if `last_booking_age_days > 30` or never; **ACTIONABLE** if ≤ 30 | A prospect with arrivals and no bookings is the expected shape and owes no action. A prospect that **has** booked inside 30 days is not a prospect — the class is stale, or the booking is misattributed. Either way it is a real finding: raise the class disagreement and check attribution against `office_identity_kind` on those lines. | Nothing to resolve in the silent case. In the contradiction case: the class is corrected, or the misattribution is named. | Do not treat a booking prospect as noise. Do not assume `ignored` means "never contact" — it means *not a served client*, which is a sales fact, not a page instruction. |
| **unknown** (no snapshot row) | **ACTIONABLE — but the first action is about the snapshot** | Check `snapshot_age_days` on the page header: if `STALE` is printed, the refresh defer has fired (DW-6) and the action is *refresh the snapshot*. If the snapshot is fresh and the guid is still absent, the office post-dates the 2026-09-11 read — a newly-onboarded office, which is precisely where onboarding failures live. **Then route on `last_booking_age_days` like any other row**, treating the office as `activating` until classed. | The guid acquires a class on the next snapshot, **or** it is confirmed as post-snapshot onboarding and handled as `activating`. | Do not guess the class. Do not assume `unknown` means `dark` — that assumption inverts the instrument (a new office that never books would be silently forgiven). **Do not let the missing class block the booking-recency read**: `last_booking_age_days` is on the row regardless. |
| **`***` residual** | **N/A — cannot occur** | `***` is excluded from floor evaluation (D5.3): neither "arrivals for this office" nor "bookings for this office" is defined for an aggregate over an unknown number of offices. It appears only as section [4]. | — | Do not evaluate it. If a `FLOOR-ZERO` row ever carries `***`, that is an **evaluator defect**, not a floor breach — file it against the build, do not investigate an office. |

#### `FLOOR-RATE` × office class

Routing key: `last_booking_age_days`. **Note that a `FLOOR-RATE` firing entails `bookings ≥ 1` in
the 3-day window**, so `last_booking_age_days ≤ 30` holds for *every* RATE row by construction —
**every `FLOOR-RATE` page is ACTIONABLE, in every class.** The class still changes the *question*.

| office class | disposition | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| **active** | **ACTIONABLE — the class the instrument was chartered on** | This is the founding shape: mail keeps arriving, a trickle books, the collapse is invisible at the booking plane because bookings are not zero. Open `/aws/lambda/autom8-email-booking-intake` with `Q-S1` over the page's window filtered to this guid and read *what the arrivals are being declined for* — `terminal_decline` reasons, `ad_lead_gate_refused`, `booking_gate_declined`. The question is "what changed in the gate", not "is the office alive". **No fragility check is needed**: §4.2 shows this floor is robust to test traffic by 14 to 249 arrivals. | The rate recovers above r, **or** the decline reason is named and routed with an owner. | Never contact a client from the page. Do not re-tune `r` to silence it — ADR D1.7 binds: a threshold is the operator's, and a seat that re-tunes after a page has broken the instrument's calibration on the record. |
| **activating** | **ACTIONABLE** | Same read as active, with the onboarding question first: a partially-wired funnel can produce a trickle. Route to the onboarding owner with the decline reasons attached. | A first-class booking rate is established or the wiring gap is named. | Do not average it against mature offices. |
| **dark-at-Offer-grain** | **ACTIONABLE — and the class contradiction is a second finding** | A dark-classed office that books at all is a class contradiction, and it is a **measured** one. Work the rate exactly as `active`, **and** raise the class. *(Worked instance, re-anchored per C-1: the sizing read flags `15caa02c` as "resolved fine, classified dark", but `15caa02c` is **absent from the landing E2 snapshot** and would therefore render `class=unknown`, not `dark`, on a live page. The disagreement it documents is real and is why E4 was rejected — the cell cannot cite it as a reproducible dark-class example. The reproducible instances are `87bd31d7` and `6b93fb76`, on the ZERO floor.)* | The rate recovers, **and** the class is adjudicated. | Do not treat the contradiction as an instrument defect — E4 (derive class from booking history) was **rejected** precisely because the two provably disagree. Do not stand down on the class. |
| **ignored** (prospect) | **ACTIONABLE — read the class first** | `933a026c` is `ignored` and is S1.1's nearest-quiet-office control at 3.70 % (K4) — comfortably above `r`, so it is not expected to fire. If an `ignored` office **does** fire RATE, the first question is whether the class is stale (it is booking) before the rate question. | The class is corrected, or the rate is explained. | Do not route a prospect to the client-relationship path before the class is adjudicated. |
| **unknown** | **ACTIONABLE — snapshot-first, then rate** | As `FLOOR-ZERO` × unknown: the missing class is the first finding, then read the rate exactly as `active`. | As above. | Do not guess the class; do not let it block the rate read. |
| **`***` residual** | **N/A — cannot occur** | Excluded from evaluation (D5.3). | — | As above: a `***` row in a floor section is a build defect. |

#### `FLOOR-REFUSED` × office class — **office class does not vary the action**

| office class | disposition | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| all six, identically | **ACTIONABLE — and it is an instrument incident, not an office incident** | The page carries `query_status`, `records_scanned`, `offices_with_bookings`, `control_reason`, the window, and the literal sentence *"no floor verdict was produced for this run"*. Read `control_reason` and triage which leg failed: `records_scanned < 500` points at a wrong log group, a wrong epoch window, or a truncated result; `offices_with_bookings < 5` is the **discriminating** half and points at a mis-scoped filter or an empty interval; `query_status != Complete` points at Insights itself. Route to the platform owner. | The next 11:00Z run publishes a `FLOOR-DIGEST` with a passing control. | **Do not conclude that no office is below floor.** A refusal is not a quiet verdict — that inversion is the exact defect D2.6 was written to forbid. Do not look for an office name on this page: there is none, by construction, and its absence is correct. Do not clear it by re-running by hand and reading the output as the day's verdict. |

**Why this row matters more than it looks.** `FLOOR-REFUSED` is the only *emitted floor class* that
can be mistaken for good news — every other one names a problem; this one names *the absence of an
answer*. (The modal page, §1.1.1, is a different and larger case.) The withheld
`LastSuccessTimestamp` (D2.6) is the wire that carries the off-hours case to the alarm plane, so a
reader who ignores a refusal page will still be reached — **once the deadman is armed at the real
topic.** Until the word (§2), that wire ends in a scratch topic.

#### `DEADMAN-liveness` (prober / freshness) × office class — **office class does not vary the action**

| office class | disposition | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| all six, identically | **ACTIONABLE — the instrument itself is dark** | The evaluator has not invoked for ≥ 7200 s plus two 3600 s breaching periods (≈ 4 h). Check the EventBridge rule `module.office_floor.schedule_rule_name` is enabled, then the Lambda's own errors alarm. Restore, and confirm the gauge drops and the alarm returns OK via `ok_actions` — **both poles, the restore leg is not optional** (D2.7 Leg 1). | `OK with datapoints present` — **not** `INSUFFICIENT_DATA`. That discrimination is the one `ebi-booking-liveness-dark` failed (charge §3); an alarm sitting in INSUFFICIENT_DATA is a dark instrument wearing a green light. | Do not assume "no page today" meant "no office below floor" for the dark interval — **the floor was not evaluated at all.** Do not kill the prober to test this alarm: a MISSING gauge is treated `missing` and **does not page** (D2.3, the inverted premise). |

#### `DEADMAN-success-gap` × office class — **office class does not vary the action**

| office class | disposition | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| all six, identically | **ACTIONABLE — the instrument runs but is not trustworthy** | Two consecutive in-run control failures (≈ 2 h at the D3 cadence) have withheld `LastSuccessTimestamp`. This is `FLOOR-REFUSED` escalated by persistence: same triage, higher confidence that the cause is structural (a wrong log group, an emptied window, a permissions regression on `logs:StartQuery`). Route to the platform owner as a sustained fault. | A controlled run emits `LastSuccessTimestamp` again and the alarm returns OK. | Do not clear it by relaxing the control floors (`records_scanned ≥ 500`, `offices_with_bookings ≥ 5`). Those floors sit at ≈ 7 % and ≈ 23 % of the *smallest observed* value; loosening them to stop a page converts the instrument into a rubber stamp. |

### §1.1.1 THE MODAL PAGE — a digest whose `[1] ACTIONABLE` section prints `(none)`

**This is the page the reader will see most often, and rev 1 did not govern it at all.** D8.1 rules
that an empty section prints its header with `(none)` — so on a healthy day the digest arrives,
every day, with nothing to do. It is the page that most reads as good news, and the one most likely
to train a reader to stop reading.

| disposition | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|
| **EXPECTED SILENCE — but only after a two-second check** | **Do nothing about any office.** Confirm the instrument ran and was trustworthy, from the digest's own header, which is the whole of the reader's job: `control : PASS`, `query_status=Complete`, `records_scanned` present and plausible (S1.1 baselines: ~66k over 8 d, ~31k over 3 d), `offices_with_bookings` ≥ 5, and `snapshot:` without a `STALE` marker. Then stop. | Nothing to resolve. The digest arriving *with a passing control and an empty ACTIONABLE section* is the instrument's healthy state. | **Do not read `(none)` alone as "no office is below floor."** `(none)` under `control : PASS` means that; `(none)` on a page that never arrived means nothing at all. **The absence of a page is not this row** — that is `DEADMAN-liveness`, and it is the reason the deadman exists. Do not stop reading the header because the sections are empty: the header is the part that carries the verdict's trustworthiness. Do not treat a `STALE` snapshot marker as cosmetic — under §1.0.1 it means the class context beside every row is unreliable, though the routing key is not. |

**The discrimination this row exists to teach.** Three different things look identical to a reader
who only skims for office names: *(i)* a healthy empty digest, *(ii)* a `FLOOR-REFUSED` page, and
*(iii)* no page at all. They mean, respectively: nothing is wrong; **we do not know** whether
anything is wrong; and **the instrument is dark**. The header fields are what tell them apart.

### §1.2 Worked examples from the measured substrate — the two stall shapes vs the ten dark ones

S1.1's K3 enumerated the `FLOOR-ZERO` firing set completely: **12 members in window A, 6 in B, 3 in
C, no unexplained member in any window** (K3 PASS). The split below is the reader's whole job on
this floor, and the substrate shows it is roughly 1-in-6. **The E2 class column is the landing
snapshot (#449); note that it agrees with the shape on 10 rows and contradicts it on 2 — which is
why §1.0.1 demoted it from router to context.**

**Shape (a) — the true stall. 2 of 12 in window A. This is what the ZERO floor is FOR.**

| guid8 | window-A arrivals | 30 d arrivals | 30 d bookings | E2 class | sizing-read bookings | why it is a stall |
|---|---|---|---|---|---|---|
| `87bd31d7` | 33 | 106 | **12** | **`inactive`** | **15** | Books 12× in 30 days and booked **nothing** in the window. A live booking relationship that *stopped*. |
| `6b93fb76` | 24 | 58 | **4** | **`inactive`** | **10** | Books 4× in 30 days, silent in the window. Same shape, thinner history. |

Both persist into window B (12 and 11 arrivals). **Reader's action:** the
`dark-at-Offer-grain, last_booking_age_days ≤ 30` row — work it as a stall, and raise the class
disagreement as a second finding. Both are far above the ±1 boundary (`87bd31d7` would need 29
synthetic arrivals to go quiet, `6b93fb76` 20), so §4.2 clears them quickly. These two are why the
ZERO floor is **not merely a dark-office detector** — and why class may not route.

**Shape (b) — structurally dark. 10 of 12 in window A. EXPECTED SILENCE, printed on purpose.**

| guid8 | window-A arrivals | 30 d bookings | E2 class | note |
|---|---|---|---|---|
| `e63bbbe0` | 24 | 0 | `unknown` (absent) | persists A/B/C — the most persistent dark member |
| `8a9b1a84` | 15 | 0 | `unknown` (absent) | persists A/B/C |
| `40f86e73` | 13 | 0 | `inactive` | **known-DISABLED office** (ADR D5.4), persists A/B/C |
| `ea98e732` | 8 | 0 | `unknown` (absent) | |
| `5a19f1ad` | 7 | 0 | `unknown` (absent) | **no resolvable `office_name`** — renders as a guid-prefix-only row (`<guid8> —`) |
| `e5a68603` | 6 | 0 | `unknown` (absent) | **known MALFORMED-GUID office** (ADR D5.4) |
| `cf6ae0f2` | 6 | 0 | `inactive` | |
| `2b591e43` | 5 | 0 | `unknown` (absent) | sits **exactly at A = 5** → see §4.2 |
| `2786b72d` | 5 | 0 | `unknown` (absent) | sits **exactly at A = 5** → see §4.2 |
| `735416d5` | 5 | 0 | `unknown` (absent) | sits **exactly at A = 5** → see §4.2 |

**Reader's action:** none — all ten have `last_booking_age_days > 30` (0 bookings in the 30-day
lookback), which is what puts them in EXPECTED SILENCE. **Eight of the ten carry `class=unknown`**
because the snapshot has no row for them; under §1.0.1 that no longer misroutes them, because the
routing key is booking recency and not class. Their `unknown` label is still a finding for DW-2 —
it means the reader sees ten rows annotated "we don't know what this is" — but it no longer
converts into ten actionable rows.

Note also that `40f86e73` and `e5a68603` are named by the ADR as disabled and malformed, and D5.4
predicts both will fall below A = 5 under the ruled unit **by the arithmetic, not by a suppression
list**. Window C bears this out: the firing set collapses to 3.

**`***` — the residual, worked.** FACT-3 (S1.1) discharged its composition: over 09-04..09-14 the
bucket is **100 % `guid_carrier = flat`** and splits `office_identity_kind` **`absent` 133 lines ·
field-absent 23 · `resolved` 0**. So `***` is *"identity never resolved at the line"*, not *"guid
present but unresolvable to a name"*. **The runbook action is therefore "the resolver did not
fire", never "the name lookup failed".** Measured share: 8.3 % (A) / 11.2 % (B) / 3.7 % (C) of
window lines — so the D5.3 `> 10 %` tripwire (`residual share HIGH — office attribution is
degrading`) is **live at today's rates and will speak on the first page**. That is intended. The
reader treats a HIGH residual as an *attribution* incident routed to the platform owner, never as
an office incident, and never contacts anyone about it.

---

## §2 THE CONSUMER STATE

### §2.0 The state, stated

The sentence below is a **synthesis** of R-168, sitting XI §4.4 and the §6 standing fence — every
clause is on the record; the sentence as a whole is this seat's composition. The operator's own
words are quoted verbatim in §3. (The token `WITHHELD` is the sitting's own, uppercase, at §6:
*"S1.2 = runbook + the word recorded as WITHHELD."*)

> **WITHHELD — R-168, sitting XI, 2026-09-14: no human has committed to act on platform_alerts
> within one business day; every page path is on the scratch topic; S1.7 is REFUSED-CORRECTLY.**

This supersedes charge §6's R-154 sentence (*"the page goes to `platform_alerts` … the human who
acts is the operator"*) on its consumer clause. Charge §6 anticipated exactly this outcome and
wrote its own defeat condition: *"if no human will act within one business day, S-1 is not armed."*
The charge's condition fired. This is the charge working, not the charge being overridden.

### §2.1 The ONE terraform change that re-points the page paths

**On the word, the re-point is one variable, in one file, with one value swapped.** The builder
(S1.3) exposes it deliberately so that arming is a value change and not a design change:

| what | the builder's contract |
|---|---|
| file | `autom8y:terraform/services/email-booking-intake/office_floor.tf` — the S-1 evaluator's own terraform, sibling to the existing `contente_booking_reconcile.tf` in that directory |
| variable | a **single** `page_topic_arn` with **two consumers**: (1) the **digest path** — the publish target passed to the Lambda's environment, carrying `FLOOR-ZERO`/`FLOOR-RATE`/`FLOOR-REFUSED`; (2) the **alarm path** — the `alarm_actions` list of the `service-lambda-scheduled` module instance, which the module shares across its freshness alarm, its self-deadman and its success-gap alarm |
| value **today** | the **scratch topic ARN**. Not `platform_alerts`. |
| value **on the word** | `data.terraform_remote_state.shared.outputs.platform_alerts_topic_arn` |
| the change | that one assignment. No resource is added, renamed or destroyed by the re-point. |

`[UV-P: the file autom8y:terraform/services/email-booking-intake/office_floor.tf and the variable page_topic_arn behave as described | METHOD: deferred-to-S1.3-build | REASON: the evaluator and its terraform are unbuilt at S1.2; this is the contract S1.3 must satisfy, not an observation of a present primitive — SVR AP-4, design-choice masquerading as platform-behavior]`

**A conflict the builder must be handed, not discover.** ADR D2.4's ⚠ ARMING ORDER paragraph
**rejects** the scratch-topic shape and rules two module instances, both with
`alarm_actions = [platform_alerts]` — instance 1 at S1.5, instance 2 (the success-gap alarm) at
S1.7 after the ≥ 7 d soak. Sitting XI **R-168 displaces that** for this wave: §6 EXECUTION ORDER
says *"page paths on the scratch topic; deadman proven both ways there"*, and the shape's S1.3
mission says *"all `alarm_actions` on a SCRATCH topic, success-gap alarm NOT yet created"*.

The displacement is coherent, and the reason is worth stating: D2.4's objection was that a scratch
topic would *"arm the liveness deadman into a void"*. Under R-168 **`platform_alerts` IS the void**
— no human has committed to read it. Pointing at it would not arm the deadman; it would only make
the void harder to see. The scratch topic is the **honest** rendering of a withheld consumer. The
sitting is later in the chain, is the decision space of record, and R-162 merely *delegated* the
deadman posture to ADR D2 — a delegated ruling cannot outrank the delegating body's own later value
ruling. **The sitting governs.**

**⚠ What survives of D2.4, corrected (C-4).** Rev 1 said the ADR's *"two-instance sequencing
survives intact"*. That over-reached. **The sequencing survives; its two-instance rationale does
not.** D2.4's two-instance structure exists *because of the topic split* — *"It is therefore
impossible, within one module instance, to point the success-gap at a scratch topic while the
freshness alarm pages `platform_alerts`."* Remove the split (all actions on scratch) and that
rationale is gone: **a single instance with the opt-in success-gap alarm enabled later satisfies
everything that remains.** What remains is the **timing**: create the success-gap alarm only after
the ≥ 7 d metric soak, so `treat_missing_data="breaching"` does not self-page at apply (D2.4's own
`main.tf:454-458` receipt of an alarm on an empty `LastSuccessTimestamp` reaching ALARM in ~2 min).
S1.3 should build the sequence, not the structure.

**⚠ A live trap in the ADR, and the erratum that cures it (C-4).** D2.4 is headed **⚠ ARMING ORDER**
and reads as the authoritative arming instruction; **D2.7 carries the same trap twice more** (Leg 1:
*"Observe the SNS delivery on `platform_alerts`"*; Leg 2's configuration receipt: *"actions = the
`platform_alerts` ARN"*). All three are **false under R-168**. A builder who opens the ADR at D2.4 —
as its own framing invites — and does not also read sitting XI §6 will wire
`alarm_actions = [platform_alerts]` at S1.5 and breach the standing fence on the day of the apply.
**An erratum on D2.4 and D2.7 is being landed by the main thread**; authorship belongs to the
architect, not to this seat and not to the critic. **Until it lands, this runbook is the notice: on
the topic question, R-168 governs and the ADR's `platform_alerts` assertions at D2.4 and D2.7 are
superseded in part.**

### §2.2 The receipts that prove the re-point — **TWO, one per consumer**

A terraform apply is not evidence that a page reaches a reader, and **one receipt proves one path**.
`page_topic_arn` has two consumers (§2.1), so the re-point takes **two symmetric receipts**. Rev 1
carried only the alarm one, which would have certified the re-point on the half that matters least.

**Receipt A — the ALARM path.**

1. Apply the one-variable change.
2. Fire a probe on the real mechanism: `aws cloudwatch set-alarm-state --alarm-name
   autom8-ebi-booking-floor-freshness-prober-liveness --state-value ALARM`, then `--state-value OK`.
   (This proves the **action path**, explicitly **not** the detection path — D2.7 Leg 2 requires
   that distinction be stated in words, and it is stated here.)
3. **The receipt is an SNS `MessageId` published on `platform_alerts`** for that probe, captured
   with its UTC instant, plus the delivery observed on the topic — never merely the alarm's state
   transition.

**Receipt B — the DIGEST path (the one that carries the product).** The Lambda env consumer carries
every `FLOOR-ZERO`, `FLOOR-RATE` and `FLOOR-REFUSED` page. An alarm-driven receipt says nothing
about it.

1. Observe a **real evaluation publish** on `platform_alerts`: either the next 11:00Z
   `FLOOR-DIGEST` run, or an S1.4-style forced `FLOOR-REFUSED` (the honest lever — point the
   evaluator's window at a deliberately empty interval via `FLOOR_WINDOW_OVERRIDE`, a
   deliberately-broken **input** the live surface correctly refuses, never a defect injected into
   working code, per `discriminating-canary-doctrine`).
2. **The receipt is that publish's SNS `MessageId` on `platform_alerts`**, with its UTC instant and
   the matching `office_floor_evaluated` log line (`paged=true`, `page_class`) for the same run.

**The negative pole, and how absence is observed.** For each receipt, the same probe fired **before**
the re-point must yield a `MessageId` on the **scratch** topic and **none** on `platform_alerts`.
An unobserved absence is not a receipt: the absence is evidenced by the
`AWS/SNS NumberOfMessagesPublished` datapoint for the `platform_alerts` topic over the probe
interval reading **zero**, captured alongside the scratch-topic `MessageId`. Two-sided, on the real
channel, per path.

Without both A and B the re-point is unproven. An `aws sns publish` from a laptop proves the topic
accepts messages and passes identically on a **silent full no-op** (an unchanged `alarm_actions`);
only an alarm-driven and an evaluation-driven delivery prove the two page paths were re-pointed.

---

## §3 THE WITHHELD WORD — instant, owner, and the exact sentence

| | |
|---|---|
| **instant of withholding** | **2026-09-14**, sitting XI, S0b (`.ledge/decisions/RATIFICATION-decision-space-sitting-XI-2026-09-14.md` §1 R-168) |
| **the words given** | *"Nobody yet: build, prove, do not arm."* |
| **owner of the word** | **the operator** (Tom Tenuta). Not the seat, not the architect, not any critic. The sitting records this as a **value** ruling, and sitting XI §5 banks the operator's feedback that only value questions come to him — this is one of them. |
| **consequence already taken** | S1.7 is **REFUSED-CORRECTLY**; R1 is **NOT REALIZED** this wave; the wave's honest ceiling is *"instrument proven, reader withheld, blocker named with its instant."* |
| **what unblocks** | nothing but the word. No build, no receipt, no critic verdict substitutes for it. |

**The exact sentence the operator would say to give it** — and it must carry all four parts:

> **"I will read `platform_alerts` and act on an S-1 page within one business day, starting
> {DATE}; point the page paths at `platform_alerts`."**

| part | why it is load-bearing | provenance |
|---|---|---|
| **a named human** (*I*, or a named other) | "the team will watch it" is the hero-culture failure mode and a bus factor of zero | **on the record** — R-168's own option set: *"I do within one business day · someone else · …"* |
| **one business day** | it is what converts a notification into a commitment | **on the record** — the same option text, plus R-154 |
| **a start date** | the commitment acquires an instant, so its absence is later detectable | **on the record** — sitting §3: the commitment waits on *"the operator, on the record **with an instant**"* |
| **the explicit re-point instruction** | the seat must never infer arming from enthusiasm | **this seat's addition, authored not quoted.** The §6 fence says paths stay on scratch *until the word*; it does not require the word to contain the re-point clause. Stricter than the record, and therefore safe. |

### §3.1 A partial word (`FLOOR-RATE` only) — **A QUESTION FOR THE NEXT SITTING, NOT A LAWFUL PATH**

Rev 1 offered a partial sentence arming the RATE floor alone, on the reasoning that R-169's
smoke-lead exposure binds the ZERO floor and not the RATE floor. **That was a sprint artifact
narrowing an operator value ruling, and it is withdrawn as a path.**

R-169 reads: *"the convention is named by the operator and codified (F5-1) **before any arming**."*
**Unqualified.** Rev 1 narrowed it to `FLOOR-ZERO` on the authority of S1.1 §6.1 — and S1.1 is the
**lowest** tier in this runbook's own §0 precedence chain (sitting → ADR → charge → OBS). A seat
acting on rev 1's partial sentence would have armed **in breach of R-169**.

**What is true, and what it is not.** The measurement stands: the RATE floor is robust to smoke
traffic by 14–249 arrivals and the ZERO floor flips on ±1 (§4.2). That is a *reason the operator
might choose* to narrow R-169 — it is not the narrowing. **Only the operator can narrow R-169, and
only at a sitting.**

**Therefore this is recorded as a question for the operator's next sitting, not as an available
sentence:**

> *Does R-169's pre-arming codification requirement bind both floors, or the `FLOOR-ZERO` class
> only? S1.1 §6.1 measured the exposure as ±1 arrival on ZERO and 14–249 arrivals on RATE. If the
> operator wishes to arm RATE ahead of the smoke-lead convention, R-169 requires an explicit
> narrowing clause in the same breath — e.g. "…and R-169's pre-arming codification binds the
> `FLOOR-ZERO` class only."*

Until that question is put and answered, **the only lawful word is the full one in §3**, and DW-3
blocks arming for **both** floors.

---

## §4 WHAT THE READER CHECKS BEFORE ACTING

### §4.1 The day-N counter (R-167) — what "day N below floor" means to the reader

R-167 ruled: **a page every day with a day count** (mechanism M3, ADR D7 — state-free, computed
from a widened lookback, ≈ 35 MB/run, no prior-state store). The operator rejected both
page-once-per-incident and plain-daily.

**What the number is.** `day N below floor` = the count of trailing rolling 3-day windows in which
this office was below the same floor, folded in memory from one Insights pass with `bin(1d)`.
N is capped at the lookback (`N_max = 14`; the scan is 17 days).

**What the number means to the reader, in four readings:**

| reading | meaning | disposition |
|---|---|---|
| `day 1` | a **new crossing**. The office was above the floor yesterday. | Highest attention. This is the transition a once-per-incident policy would have shown and a plain-daily policy would have buried. |
| `day 2–3` | still new, and the 3-day window still overlaps the crossing. | Act. |
| `day 4+` | a **standing** condition. Someone has seen this before. | Act, and ask the second question: *why is this still here?* A standing page is either un-actioned work or a mis-classed office. Both are findings. |
| `day N = N_max` (14) | the counter is **saturated**, not necessarily accurate. | Treat 14 as "≥ 14". Do **not** read a plateau at 14 as stabilisation. |

**What the counter is NOT.** It is not state. There is no store, so a counter that resets is not
evidence that anything was fixed — it is evidence that the office rose above the floor in the
lookback, which may be a single arrival's worth of arithmetic. **`N` resetting is never a
resolution receipt.** Resolution is defined per cell in §1.1 and never by the counter alone.

**Do not confuse `day N` with `last_booking_age_days`.** They are different clocks and they answer
different questions: `day N` counts *how long this office has been below the floor* (the urgency
gradient); `last_booking_age_days` says *whether this office books at all* (the routing key,
§1.0.1). An office can be `day 1` and dark, or `day 12` and a stall.

**The fatigue warning, stated because it is the known cost of M3.** Every standing office pages
every day. ADR D7 named reader fatigue as M1/M3's risk and routed it to the consumer question,
which is now withheld. When the word comes, the first week's page volume is the operator's
calibration data — and M4 (repeats past N days route to a lower-urgency channel) is the designed
relief valve, unbuilt, requiring its own two-sided proof and its own soak.

### §4.2 The false-positive channel from unmarked test leads (R-169) — the fragile floor

R-169 ruled: **test leads go through real offices with no marker today.** S1.1 confirmed the
consequence own-hands: there is **no marker field, no reserved guid, and no `is_test` / `smoke`
predicate anywhere on the office-bearing lines**. A side-by-side "with exclusions" table is
**unconstructible, not omitted**. Live evaluation therefore counts smoke leads as real arrivals.

S1.1 sized the exposure. It is sharply asymmetric:

| | `FLOOR-RATE` (the primary class) | `FLOOR-ZERO` (the secondary class) |
|---|---|---|
| synthetic arrivals to **silence** the founding office | **249 / 68 / 19** (67.5 % / 36.2 % / 19.2 % of its entire traffic) | — |
| synthetic arrivals to **falsely fire** the nearest quiet office | **≥ 14** (`933a026c`, window A) | **1** |
| verdict | **ROBUST.** No plausible smoke volume reaches these numbers. | **FRAGILE at the boundary: ±1 arrival.** |

**In window A, 18 offices sit below `A = 5` with zero bookings** — every one of them is one
synthetic arrival away from firing. Three offices sit at **exactly 4** (`7081d9d4`, `fa59bf58`,
`783b40aa` — one arrival each), and three fired members sit at **exactly 5** (`2b591e43`,
`2786b72d`, `735416d5` — one arrival from going quiet).

**⚠ `783b40aa` is `active` in the landing snapshot.** So a single unmarked smoke lead can
manufacture a `FLOOR-ZERO` page on an **active** office — the grid's highest-urgency cell, whose
instruction begins *"Run the §4.2 fragility check first."* The loop closes correctly, and naming
that one of the boundary offices is `active` is what makes the ±1 exposure legible rather than
abstract.

**THE CHECK, before acting on any `FLOOR-ZERO` page.** Three questions, in order:

1. **Is `arrivals` at or near 5?** If `arrivals ∈ {5, 6, 7}`, the verdict may rest on one or two
   lines. Treat it as provisional until step 2. *(On the page — zero reader work.)*
2. **Did anyone run a smoke test through this office in the window?** There is no field to ask, so
   **ask the operator** — who is both the page's addressee and, until DW-3 closes, the only party
   who knows what smoke traffic was run. Record the answer on the page thread either way; that
   record is the substrate the eventual convention will be built from. *(Not on the page, no
   instrument behind it — the un-automatable step, disclosed and owned.)*
3. **Does the `day N` counter say 1?** A brand-new `FLOOR-ZERO` crossing at `arrivals = 5` is the
   highest-prior smoke artefact in the whole instrument. A day-4+ standing zero at `arrivals = 5`
   is far more likely to be real: smoke traffic does not usually persist for four consecutive
   windows. *(On the page — R-167 ruled the day count printed.)*

**No such check is required before acting on a `FLOOR-RATE` page.** The arithmetic says the founding
class cannot be created or destroyed by test traffic. A reader who applies the fragility check to
a RATE page is spending attention the instrument does not need — and, worse, is rehearsing a habit
of doubting the one class that is robust.

**The gate, stated at one strength (C-3).** R-169 binds the convention's codification **before any
arming, both floors** — see §3.1. This section's measurement explains *why the exposure differs by
floor*; it does **not** narrow the gate, and DW-3 below reads at the same strength. Under R-169
honoured, step 2 should never fire on a live page at all.

**The cure, and its owner.** The durable fix is a reserved test office or a marker field (packet
F5-4); the interim fix is the operator **naming** the convention (F5-1). UV-P-1 stays open with the
**operator** as owner. See DW-3.

---

## §5 DEFER-WATCH MANIFEST

Everything this runbook depends on that does not yet exist. Per `defer-watch-manifest`: each item
carries an owner, a refutable watch-trigger, and an escalation path. **No row is `NO WATCHER`** —
the sitting's own rule.

| id | item | deferral rationale | watch-trigger (refutable) | owner | escalation | blocks arming? |
|---|---|---|---|---|---|---|
| **DW-1** | **The E2 class snapshot source.** ADR D5.1 rules a build-time constant sourced from `READ-offer-activity-sizing-2026-09-11`; at S1.1 that artifact was in neither the working tree nor `origin/main`. | It was taken 2026-09-11 and cited by charge §7 but never landed to a ref. | `git ls-tree -r --name-only origin/main \| grep offer-activity-sizing` non-empty **AND** the evaluator's checked-in data file carries `snapshot_date = 2026-09-11`. **Well-formed and expected to fire on #449's merge** (the JSON carries `"snapshot_date": "2026-09-11"`). | **platform-engineer (S1.3)** | If unresolvable at S1.3, the builder **recedes to the operator** — do not substitute a plane-derived proxy (that is E4, explicitly rejected by ADR D5.2). | narrowed by #449 |
| **DW-2** | **The office-class axis is not a safe router — restated on measured numbers (C-1).** Joined against the landing snapshot: **8 of 12** window-A `FLOOR-ZERO` members render `class=unknown` (not 10, as rev 1 estimated) — **and, worse, 2 of 2 genuine stalls (`87bd31d7`, `6b93fb76`) carry `class=inactive`**, which rev 1's grid routed to EXPECTED SILENCE. | Rev 1 promoted an annotation that was never validated as a routing key into one. | The digest renders `last_booking_age_days` on every row **and** section membership keys on it (not on class) — verified by an S1.4 probe in which an `inactive`-classed office with a booking inside 30 days lands in `[1] ACTIONABLE`. | **platform-engineer (S1.3)**, with §1.0.1 as the contract | **The snapshot landing NARROWS this defer; it does not discharge it.** Arming before the routing key lands re-creates the founding silence inside the instrument. | **YES** |
| **DW-3** | **The smoke-lead convention (R-169 / F5-1) is unnamed.** VERIFIED-ABSENT in code at both repos; no marker, no reserved guid, no predicate. §4.2 step 2 is a human question with no instrument behind it. | The operator ruled the current practice (real offices, no marker) and reserved the convention to himself. | The operator names the convention **and** it is codified in a ref-resolvable artifact. Durable form = F5-4 reserved office. | **operator** (UV-P-1 owner, per sitting XI §3) | R-169 binds **before any arming, unqualified**. Any narrowing to one floor is an operator ruling at a sitting (§3.1), never a seat's. | **YES — both floors** |
| **DW-4** | **The consumer commitment itself** (§2, §3). | R-168, recorded with its instant. | The operator speaks a §3 sentence, on the record, with a start date. | **operator** | Nothing else unblocks it. S1.7 stays REFUSED-CORRECTLY; the handoff says so in line one. | **YES — this is the arming gate** |
| **DW-5** | **`office_floor.tf` / `page_topic_arn` do not exist yet** (the §2.1 UV-P). | S1.2 is record-only; the build is S1.3. | The file exists at `autom8y:terraform/services/email-booking-intake/office_floor.tf` and exposes exactly one `page_topic_arn` feeding **both** the Lambda env digest target and the module's `alarm_actions`. | **platform-engineer (S1.3)** | If the builder exposes **two** topic variables (or hard-codes either path), §2.1's "one change" promise is void and §2 must be re-authored before arming. | **YES** |
| **DW-6** | **The snapshot-refresh cycle** (ADR D5.1 rule 3). | Deliberately self-surfacing: the page emits its own staleness. | `snapshot_age_days > 30` appears on any page (renders `STALE` on every row). | **the operator**, via §1.1's `unknown` row and §1.1.1; **watcher = the page itself** | Refresh = a read-only re-run of the sizing read. If the page is unread (the current state), this watcher is **also dark** — self-surfacing only once DW-4 closes. | no (see note) |
| **DW-7** | **`contente_booking_allowlist_suppressed` is unclassified.** S1.1 FACT-3 found 4 window-A lines of an office-bearing event that ADR D1.1's terminal set does not enumerate. | Raised as a UV-P by S1.1 rather than silently folded into the unit. | The builder either adds it to the terminal set with a ruling, or records it as deliberately excluded with a reason. | **platform-engineer (S1.3)**, escalating to the architect | Silent inclusion changes the arrival unit without a ruling — an ADR D1 breach. Silent exclusion is acceptable **only if stated**. | no |
| **DW-8** | **The `FLOOR-REFUSED` and `DEADMAN-*` page bodies are specified but unrendered.** §1.1's triage rows assume D2.6's fields are actually on the page. | The evaluator is unbuilt. | S1.4's `FLOOR-REFUSED` probe receipt shows all six elements present in the published body. | **chaos-engineer (S1.4)** | If any field is missing, §1.1's `FLOOR-REFUSED` row is unexecutable and must be re-authored before arming. | **YES** |
| **DW-9** | **The guid8 → office → owner lookup is not a named path (C-5).** The page carries guid8 only (correct per fences), so from the page alone the reader cannot name the office, let alone reach whoever owns the relationship. Every floor cell that says "route the client half" depends on this. | The fences are right; the lookup was simply never specified. The runbook's own §3 standard — *a named human, not a role* — applies to itself. | A named, ref-resolvable path from guid8 to the office's owning human exists (a lookup artifact, a field on the E2 snapshot, or a named person who performs the lookup on request). | **operator** (until the reader role is re-seated) | Until it closes, every client-side route in §1.1 terminates at the operator. That is workable for one reader and does not scale to a second. | no (but every client-side action funnels through the operator) |
| **DW-10** | **ADR D8.1's section predicate is superseded** (§1.0.1). D8.1 sections `[1] ACTIONABLE` on `class=active \| activating`; under C-1 it must section on `last_booking_age_days ≤ 30`. | C-1 landed after the ADR was ruled. | The evaluator's rendered digest places an `inactive`-classed office with a recent booking in `[1]` and a no-booking `inactive` office in `[2]`. | **platform-engineer (S1.3)**; ruling authority = the architect | If S1.3 builds D8.1's predicate literally, the two true stalls land in EXPECTED SILENCE and DW-2 is un-cured in code while appearing cured in prose. | **YES** |

**Note on DW-6.** A self-surfacing defer whose surface is an unread page is not self-surfacing.
This is the general shape of every watcher in this wave: **R-168 makes the page the weakest link in
every chain that ends at it.** That is not a defect in the design; it is the accurate consequence
of an unarmed instrument, and it is why the wave's exit line says the reader is withheld rather
than saying the instrument is live.

---

## §6 ANTI-THEATER SELF-CHECK

| check | result |
|---|---|
| Does any action item target a human's memory rather than a system? | §4.2 step 2 does — **knowingly**, and it is filed as DW-3 with the operator as owner, a named person to ask, and a durable cure (F5-4). It is labelled the un-automatable step, not presented as a practice. |
| Does the runbook claim S-1 is live, armed, or read? | **No.** The header, §2.0, §3 and DW-4 each state the opposite. change-warden's certification explicitly *"is not an activation GO"*. |
| Does the office-class axis suppress action anywhere? | **No — and rev 1 did.** §1.0.1 demotes class to printed context and makes `last_booking_age_days` the routing key. The two rows rev 1 would have false-silenced (`87bd31d7`, `6b93fb76`) are now ACTIONABLE by construction, and the correction is shown rather than quietly patched. |
| Is the modal page governed? | **Yes, §1.1.1** — rev 1 omitted it. The empty-ACTIONABLE digest is the page most likely to read as good news, and its row names the three states a skimming reader conflates. |
| Does any cell say "investigate" or "be careful" without a named action? | No. Every cell names what to open (log group + `Q-S1`), what to ask, what "resolved" means, an owner, and one or more prohibitions. |
| Is any claim about a not-yet-built primitive asserted as present-tense fact? | Two, both UV-P-labelled under SVR AP-4 and both with defer rows: `page_topic_arn` (§2.1, DW-5) and `last_booking_age_days` (§1.0.1, DW-2/DW-10). |
| Does a sprint artifact narrow a higher-tier ruling anywhere? | **No — rev 1 did, and §3.1 withdraws it.** The partial word is now a question for the next sitting; §4.2 and DW-3 read at one strength. |
| Are the fences held? | guid8 only throughout; **no office name appears**; **no phone digits appear**; no page path repointed; nothing merged or armed. |
| Were governance reads taken from a named ref? | Yes — `origin/main` (sitting XI), `origin/sre/s1-1-observe-20260914T040422` (S1.1), `origin/docs/e2-offer-class-snapshot-2026-09-14` (#449). Named in §0 and the frontmatter. |
| Contributing factors, not a root cause? | The instrument's failure surface is decomposed into five page classes, the modal page, and ten defer rows. §1.0.1 is itself a contributing-factors finding: the class axis was not wrong, it was *promoted* beyond what it was validated for. |

**Evidence grade: MODERATE** (`self-ref-evidence-grade-rule` ceiling; change-warden's rite-disjoint
certification is in-fleet and self-caps at MODERATE on the same rule). The runbook's subject is an
instrument that has not run. Its substrate is measured and ref-anchored; its own operational claims
— that these actions are the right actions — are **untested by construction** and remain so until a
reader exists. The honest upgrade path is not a better runbook; it is DW-4.

**The acid test.** *If the founding silence happens again, does this runbook prevent a repeat?*
**Not yet — and the reason is named with its instant.** The instrument would detect it (K1: the
founding office fires the RATE floor in all three windows). The digest would name the office. And
the page would land on a scratch topic that nobody reads. The gap between "detected" and
"prevented" is exactly one sentence from one person (§3), and this runbook's whole purpose is to
make that sentence cheap to say and impossible to say by accident.

**A second acid test, earned the hard way in rev 1.** *If the instrument pages correctly, does this
runbook get the reader to act?* Rev 1's answer was **no for the two cases that matter most** — both
true stalls carried a class label that instructed the reader to stand down. An instrument that
detects correctly and a runbook that routes incorrectly produce the same outcome as no instrument
at all. That failure was caught by a rite-disjoint critic reading the runbook against a snapshot
the runbook's author had not joined, which is the whole argument for the critic being disjoint.

---

## §7 AMENDMENT 2026-09-15 — the s1.4 page names no clinic: resolve out of band, check the lead-match share, expect one page a day

> **Appended, not rewritten.** This is P3b of `read-the-name` wave 1 (incident-commander seat, docs PR under the operator's user-grade grant R-A3, critic change-warden). §1–§6 stand as rev 2 wrote them. Where this section narrows one of their instructions, it names the section. Governance reads: autom8y-asana `origin/main 408cbc37` and autom8y `origin/main 0ee1209a`, both via `git show "${REF}:path"`. Live reads 2026-09-15T22:45Z–22:57Z, read-only, own hands, rc unpiped. Every command is committed at `.ledge/reviews/read-the-name/arm_observe.py` (this PR). It lives under `.ledge/` deliberately: `test.yml` ignores `.ledge/**` on push but not `scripts/**`, and a Test run on main dispatches the asana service deploy, so a paper PR carrying it under `scripts/` would roll the service. **This amendment arms nothing.**

### §7.0 What changed on the page

autom8y #2272 (evaluator `s1.4`, deploy run 35031971218, `completed / success` at 22:50:36Z) removed `office_name` from the per-office log line, from the digest row, and from its producer: `FloorVerdict` has no such attribute (autom8y `0ee1209a` `services/email-booking-intake/src/email_booking_intake/office_floor/handler.py:645`, marker `NO ``office_name``: it was populated on 1,526 of 1,526 lines`). **The page now identifies an office by guid8 only.** Read back at 22:52Z via `arm_observe.py F`: all five EBI functions serve `0b5e1c9`, the intake alias `live` points at v72, and the five agree. The 22:27Z run line was still `s1.3`. **DISCHARGED at the 23:27:15Z fire, the first `s1.4` scheduled run:** `evaluator_version="s1.4"`, `control="passed"`, `records_scanned=22322` (in the prior band 21184 / 21631 / 21976), `offices_unclassified=27` present, `page_message_id` **present and null** (the hour is not 11), `booking_attribution_floor_day=2026-09-09`, and a `LastSuccessTimestamp` sample in the 23:00Z bucket. The `office_name` proof is two-sided on one query: **50 of 50 office lines carried it at 22:00Z (s1.3) and 0 of 50 at 23:00Z (s1.4)**. No fence token differs, so the soak does not reset and the arm stays 09-22. The floor day reading exactly `2026-09-09` is the guid-stamping boundary — residual **E-2** as declared, not a surprise.

The standing fence requires this: no raw clinic name and no office phone on any paging surface. It also re-opens coordination hazard **H-5**. A page that names nothing a human can act on is, in this wave's own north, *"a signal nobody can act on is still silence."* §7.1 is the cure.

### §7.1 guid8 → clinic: the out-of-band lookup (narrows DW-9)

**The lookup exists and a reader can run it; it was proven today. The reader needs AWS read access.**

| | |
|---|---|
| **where** | CloudWatch Logs Insights, us-east-1, log group `/aws/lambda/autom8-email-booking-intake`. The source is the intake's own `office_resolved` line: ws-join ADR J3 (`ADR-ws-join-office-naming-path-2026-09-08.md` §1.2, `resolve_office.py:259-265` at autom8y `e292b616`), which carries the redacted guid (first 8 hex), the business name and the raw office phone **on one line** |
| **the command** | `python3 .ledge/reviews/read-the-name/arm_observe.py lookup <guid8> --print-name` from an autom8y-asana checkout, or the console query below |
| **who can run it** | any AWS principal with `logs:StartQuery` + `logs:GetQueryResults` on that log group. Today that is the operator's SSO session. `[UV-P: whether any human other than the operator holds AWS read in this account | METHOD: IAM Identity Center assignment listing for the reader the operator names | REASON: not read at P3b; the named reader's access is an arming-receipt cell]` |
| **what it returns** | one row per distinct `office_name` seen for that guid8 over 30 days, with a line count and `last_seen`. **Exactly one row means resolved.** Zero rows, or two or more, means do not guess: ask the operator (DW-9's original route) |
| **measured 2026-09-15** | **7 of 7** named offices resolve to **exactly one** name over 30 days, counted with `count_distinct` and never printed (recordsScanned 612,948): `8a9b1a84`, `e63bbbe0`, `40f86e73`, `ccb52f4c`, `5a19f1ad`, `87bd31d7`, `6b93fb76`. That includes `5a19f1ad`, which §1.2 records as having "no resolvable `office_name`" on the arrival lines; the `office_resolved` line resolves it. The committed `lookup` re-ran on `8a9b1a84` with the name withheld: 1 distinct name, 311 lines, last seen 2026-09-14 23:47Z |
| **cost** | one Insights query over ≈ 610k records, about 20–40 s |

The console query, verbatim:

```
fields @timestamp
| filter @message like /office_resolved/
| parse @message /"guid":\s*"(?<g>[0-9a-fA-F]{8})/
| parse @message /"office_name":\s*"(?<office_name>[^"]+)"/
| filter g = "<guid8>" and ispresent(office_name)
| stats count(*) as lines, max(@timestamp) as last_seen by office_name
```

**⚠ The phone rides the same line.** Every `office_resolved` line read for the 7 offices also carried a non-empty `office_phone`: 100 %, counted by pattern, never printed. The query above projects `office_name` only. **Never** run `display @message`, never add `office_phone` to the projection, never screenshot the raw event.

**The resolved name stays out of band.** `autom8y-platform-alerts` delivers to email **and** to Slack `#platform-alerts` (§7.4). Do not type a clinic name into a reply on either, or into a ticket, a PR or a ledge record: each of those is a surface the fence protects. Write the **guid8** on the page thread and keep the name off it. (This narrows §4.2 step 2's "record the answer on the page thread": the answer is recorded, the name is not.)

**What DW-9 still lacks.** The lookup resolves *guid8 → clinic*. It does not resolve *clinic → the human who owns the relationship*; that hop still ends at the operator. A reader without AWS read gets no lookup at all and routes everything through the operator. **DW-9 is narrowed, not closed.**

**Secondary path, not proven today.** The 2026-09-11 sizing read resolved guid8 against the `Company ID` custom field on Asana Business tasks, using `by_prefix()` (`READ-offer-activity-sizing-2026-09-11.md` §1 "Join of record"). That resolver was a session-scratch script over API dumps. It was never committed, and it needs an Asana PAT. `[UV-P: the Asana UI search finds a Business task from a Company ID prefix | METHOD: the operator runs one UI search for a known guid8 | REASON: not exercised at P3b; the log-plane lookup above is the proven path]`

### §7.2 Before anyone contacts a clinic about a ZERO-floor office: find out WHY it is zero (narrows §1.1)

> **CORRECTED 2026-09-15T23:35Z, before this amendment ever reached `main`.** The first draft of this
> section said: *"arrivals dominated by `LeadMatchError` sharing one From domain ⇒ the zero is our
> matcher, not the clinic."* **That rule is wrong, and it is wrong in the direction that costs most:**
> it would have had the reader report our own product, working exactly as ruled, as a defect of ours.
> The EBI lane stopped it with a specific counter-measurement, and the correction below is the result.
> Recorded rather than quietly replaced, because the wrong version is the instructive half.

§1.1 already says *never contact a client from the page*. This narrows the **client half** of every
`FLOOR-ZERO` cell — the part that routes toward the office's owner through DW-9.

```
python3 .ledge/reviews/read-the-name/arm_observe.py C <guid8>
```

**The discriminator is READ COMPLETENESS, not the sender.** The lead pool is read in two disjoint
status legs whose union is the true open-lead set. Two cases look identical from the floor — an
office at zero, its arrivals dominated by match failures, all from one sender — and they are opposite
facts about the system:

| what happened | what it means | what the reader does |
|---|---|---|
| the read lost a leg and we scored only the survivors (**PARTIAL**) | **ours.** We declined over a candidate set we never saw whole | do not call; route to the platform owner as a lead-match defect |
| the read was **COMPLETE** and found nothing to bind | **not ours.** No ad-originated lead exists for these patients: they never came from our funnel. The ratified rule books only what our funnel originated | do not call about a booking gap, and **do not report it as our bug** |

Measured 2026-09-15T23:27Z over 72 h. Failures are counted as **distinct traces**, not lines — the
`match_lead` stage emits two lines per failure (one carrying `error_type`, one not), and summing
lines put the share at 178 %:

| guid8 | arrivals | bookings | match_lead failure traces | share | partial-read traces | verdict |
|---|---|---|---|---|---|---|
| `8a9b1a84` | 9 | 0 | 8 | 89 % | **0 of 8** | **NOT AD-ORIGINATED** — complete reads, one sender |
| `e63bbbe0` | 3 | 0 | 3 | 100 % | **0 of 3** | **NOT AD-ORIGINATED** — complete reads, one sender |
| `79be1b75` | 4 | 0 | 4 | 100 % | **4 of 4** | **OURS** — every failure on a partial read |
| `ccb52f4c` | 135 | 6 | 3 | 2 % | **2 of 3** | **OURS** — the founding office is affected |
| `40f86e73` | 3 | 0 | 0 | 0 % | 0 of 0 | genuine office-side zero (the control) |

**The two zero-floor offices are NOT our defect.** Their reads were complete: 0 of 8 and 0 of 3.
Corroborated two ways — my own trace join above, on the log plane, and the EBI lane's read of the
lead database (*zero ad-attributed leads in 90 days, in any status or phone format*), which is
**theirs, not re-derived here, and carried as theirs**.

**Three cautions.**

1. **Key on `stage`, never on the error name.** Every match failure carries `stage="match_lead"` /
   `event="stage_exception"`; the `error_type` on it is a name, and autom8y #2290 renames it to
   `PartialReadNotOrganicError` for the partial subset. A filter on the name drops silently to zero
   at that deploy and reads as *no misattribution*. The observer groups **by** `error_type` under the
   stage, so the rename appears as a new label instead of a silence. `failure_kind` is not on the
   line at all (measured: absent on 25 of 25), so `stage` + `error_type` is all a reader has.
2. **Two event names, one condition.** Partial reads are marked by `name_evidence_read_partial`
   **and** `activation_lead_leg_failed`; the EBI diagnosis enumerated the defect partly through the
   second. Over 72 h each name returns the same 6 traces — intersection 6, union 6, neither
   exclusive — which is exactly the coincidence that would have hidden the gap. The observer takes
   the union.
3. **The 50 % cut is a seat heuristic, not an operator ruling.** `[PLATFORM-HEURISTIC:
   LEAD_MATCH_SHARE = 0.5]` Today's shares are 0 %, 2 %, 89 % and 100 %, so nothing measured depends
   on where it sits. If a live office lands near 50 %, ask the operator.

**Where to look first:** the ZERO-floor ∩ `class=unknown` intersection that `arm_observe.py E`
prints. The `offices_unclassified` counter is not that signal: it counts every office missing from
the snapshot and read **27** on the 23:27Z `s1.4` line.

`[UV-P: that the partial-read hop stays readable after autom8y #2290 deploys | METHOD: re-run
`arm_observe.py C` on ccb52f4c and 79be1b75 after the deploy; the by-error_type breakdown should
show PartialReadNotOrganicError appearing under stage=match_lead | REASON: the code is still under
adversary attack and has not shipped]`

### §7.3 The cadence: one page a day, and the founding office will be on most of them

- **One digest per UTC day**, published by the 11:27Z scheduled evaluation (the page gate is `hour == 11`). The other 23 hourly runs evaluate and emit `LastSuccessTimestamp` but publish nothing. R-172's at-most-one-publish rule is best-effort (handoff §5 UV-P-B), so a duplicate digest is possible but not expected.
- **The founding office `ccb52f4c` hovers at the RATE floor. It is not on it every hour.** Measured over the 48 h to 22:56Z: **27 of 43** hourly evaluations placed it on `rate` (booking rate 0.8 %–2.4 %). The other **16** were `quiet` at 3.0 %–3.8 %, just above `r = 2.5 %`, and `day_n` never exceeded **2** because each rise above the floor resets it. Expect it on **most** daily pages. When it appears it is ACTIONABLE, as the chartered shape (§1.1 `FLOOR-RATE` × active). When it is absent for a day, that is one window's arithmetic, not a recovery (§4.1: *"`N` resetting is never a resolution receipt"*). Do not ask for it to be filtered, and do not re-tune `r` to quiet it (ADR D1.7). *(The coordination seat's premise was "recurs daily". The measurement narrows that to "most days, and never read as fixed when absent".)*
- **No digest by about 12:00Z is `DEADMAN-liveness` territory (§1.1), not a quiet day.** The freshness deadman goes red only at roughly the fourth missed hourly fire (handoff §4), so a missing 11:27Z digest may be the **first** sign, hours before any alarm.

### §7.4 What else lands on `autom8y-platform-alerts`: the page is one message among about 30 a day

Read at 22:5xZ with `arm_observe.py D`:

- **Subscriptions: 2.** One **email** (confirmed) and one **Lambda**, `autom8-slack-alert` (confirmed, 0 errors in 24 h), which posts to Slack `#platform-alerts`. **No SMS.**
- **Readers: one human of record.** Both legs resolve to the operator (autom8y `OWNERSHIP-instrument-readers-of-record-2026-08-23.md` §2, handles R-MAIL-1 and R-SLACK). Slack membership beyond the operator cannot be enumerated from AWS.
- **Volume:** **347 of the account's 427 alarms** route to the topic. At the read, **46 were in ALARM**, 288 OK and 13 INSUFFICIENT_DATA. It published **28–35 messages a day** over 2026-09-11..14, and 229 on 09-08.
- **The S-1 digest adds one message a day** to that stream.

`[UV-P: autom8-slack-alert renders a plain-text evaluator digest as a readable Slack post, rather than dropping or garbling a message that is not a CloudWatch alarm JSON | METHOD: after the re-point, read autom8-slack-alert Errors for hour 11 and the Slack post itself on day 1 | REASON: every message this Lambda has handled on this topic is alarm-shaped; no evaluator digest has ever reached it]`

### §7.5 Fences held in this amendment

guid8 only. No clinic name, no phone digit, no full GUID and no account id. The lookup withholds the name by default and prints it only under an explicit flag, at the reader's own terminal. Nothing was re-pointed, merged or armed.

## §8 AMENDMENT 2026-09-24: the smoke-lead convention, codified (closes DW-3)

**Source:** the operator's word of 2026-09-24, applied per precedence. See `SLATE-read-the-name-operator-words-2026-09-16.md` §10.1.

**The convention, from the arm onward:**
1. **No smoke or test lead is sent through a real office while S-1 is armed.**
2. **A run that has to use a real office is announced on the S-1 page thread before it starts.** The announcement names the office by guid8 only, gives the UTC window, and states the expected number of synthetic arrivals.
3. **§4.2 step 2 becomes answerable from the record.** "Did anyone run a smoke test through this office in the window?" is answered by the thread. No announcement means the answer is no.

**The durable form** is a reserved test office excluded from U-3 (F5-4). It is a pinned-query change, so it lands in the post-arm bundle (slate §10.3), never during a soak.

**What this does not do.** It does not make an unannounced smoke lead detectable. Nothing on the plane marks one. The convention turns an unknowable question into a recorded one, and §4.2's ±1 fragility on `FLOOR-ZERO` still applies to any violation.

**DW-3 status: DISCHARGED by codification** (watch-trigger: *"the operator names the convention and it is codified in a ref-resolvable place"*).

### §8.1 AMENDED 2026-09-25 by the operator's ratification (slate §11 D10): ANNOUNCE ONLY, replacing item 1

**Item 1 above (the moratorium) is withdrawn.** The convention from the arm onward:
1. **Smoke and test leads MAY go through real offices at any time.**
2. **Every such run is announced on the S-1 page thread before it starts**, giving the guid8, the UTC window, and the expected number of synthetic arrivals.
3. **§4.2 step 2 is answered from the thread.** An unannounced run is a convention breach and is recorded as one.

R-169's gate (a codified convention before any arming, both floors) is still met. What announce-only does not prevent: an announced run can still produce a genuine ±1-arrival false `FLOOR-ZERO` page. **The reader knows why.** DW-3 stays DISCHARGED.

