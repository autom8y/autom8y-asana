---
type: review
artifact_kind: runbook
initiative: read-the-name
sprint: S1.2
rite: sre
station: incident-commander
created: 2026-09-14
decision_space_of_record: .ledge/decisions/RATIFICATION-decision-space-sitting-XI-2026-09-14.md
implementation_adr: .ledge/decisions/ADR-read-the-name-s1-implementation-2026-09-14.md
upstream_observation: .ledge/reviews/OBS-read-the-name-s1-2026-09-14.md   # PR #448, branch sre/s1-1-observe-20260914T040422
charge: .sos/wip/CHARGE-read-the-name-s1-per-office-floor-2026-09-11.md
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

## §0 METHOD, REFS, FENCES

**Authorities, in precedence order.** `RATIFICATION-decision-space-sitting-XI-2026-09-14.md`
(the decision space of record; R-160 · R-167 · R-168 · R-169 · R-171 · R-172) →
`ADR-read-the-name-s1-implementation-2026-09-14.md` (D1–D8, the delegated implementation rulings) →
`CHARGE-read-the-name-s1-per-office-floor-2026-09-11.md` §6 (superseded on its consumer clause, see
§2.0) → `OBS-read-the-name-s1-2026-09-14.md` (S1.1, the measured substrate: K1–K5 all PASS).

**Governance reads were taken from a named ref.** Sitting XI is present at `origin/main` and absent
from this repo's working tree; the S1.1 artifact is present only at
`origin/sre/s1-1-observe-20260914T040422`. Both were read with `git show "${REF}:path"`, never from
a checkout. (Scar: `worktree-vs-session-repo-path-trap`, five instances, one of them a false
governance fork put to the operator.)

**Fences honoured in this artifact.** guid8 only; no office names; no phone digits on any face
(charge §10, risk row 12); no page path repointed; nothing merged, nothing armed.

**What this runbook is NOT.** It is not an arming authority, not a threshold re-tuning (ADR D1.7:
on K1/K2 failure the seat recedes to the operator — K1/K2 passed, nothing was tuned), and not a
claim that S-1 is live. S-1 is **built-pending, unarmed, unread**.

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
every row with its age and a `STALE` marker past 30 days:

| office class | source | digest section |
|---|---|---|
| `active` | snapshot row, `max_offer_activity` live | [1] ACTIONABLE |
| `activating` | snapshot row, onboarding in flight | [1] ACTIONABLE |
| `dark-at-Offer-grain` (`inactive` / `dark`) | snapshot row, no live Offer | [2] EXPECTED SILENCE |
| `unknown` | **no snapshot row** for this guid — never blank, never inferred (D5.1 rule 2) | [3] CLASS UNKNOWN |
| `***` attribution residual | not an office at all (D5.3) | [4] ATTRIBUTION RESIDUAL |

**The two axes are not symmetric, and the asymmetry is load-bearing.** `FLOOR-ZERO` and
`FLOOR-RATE` are *per-office* verdicts, so the office class changes the action. `FLOOR-REFUSED`,
`DEADMAN-liveness` and `DEADMAN-success-gap` are *instrument* verdicts: **no office is named on
them and the office class does not vary the action.** That is stated as a row rather than omitted,
because the failure this instrument exists to cure is a silence nobody could act on — and an
operator who goes looking for an office name on a `FLOOR-REFUSED` page and finds none must know,
in advance, that the absence is correct and not a bug.

### §1.1 The grid — a named human action per cell

Read `WITHIN ONE BUSINESS DAY` as the R-154 business-hours contract: a page landing Friday evening
waits until Monday, accepted on the record.

#### `FLOOR-ZERO` × office class

| office class | ACTIONABLE or EXPECTED SILENCE | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| **active** | **ACTIONABLE — highest urgency on this floor** | Before anything else run the §4.2 fragility check (this floor flips on ±1 arrival). If it survives: open the office's intake path and answer *did mail arrive and produce no booking, or did the booking path fault?* Check `booking_intake_fault` and `booking_gate_declined` on the same guid in the same window. Route the mechanism half to the platform owner; route the client half to whoever owns that relationship. | The office books again, **or** a named human has decided this office is not expected to book and the class is corrected in the next snapshot. A page that stops because the window rolled is **not** resolved. | **Never contact a client from the page.** The page names an *office*, not a patient, and carries no patient identity. Never phone from it (no phone digits are on the page by construction; do not go find them). Never silence the office by adding it to a list — D5.4 forbids suppression lists; if it should be quiet, fix the **class**, not the filter. |
| **activating** | **ACTIONABLE — but a different question** | Ask *has this office ever booked?*, not *why did it stop?* This is an onboarding-completion question: the funnel head may never have been wired. Route to the onboarding owner. | Either a first booking lands, or the onboarding gap is named and ticketed with an owner. | Do not treat it as a regression. Do not conclude "the instrument is wrong" — an activating office with arrivals and zero bookings is exactly the class the charter says is structurally invisible today. |
| **dark-at-Offer-grain** | **EXPECTED SILENCE** | Read the section header and stop. No action is owed. One standing exception: if a dark office's arrivals *rise* materially across consecutive days (the day-N counter, §4.1), ask once whether the Offer-grain class is stale — the office may have reactivated without the snapshot knowing. | Nothing to resolve. The row is doing its job by being visible-and-labelled. | Do not chase it. Do not ask for it to be filtered — it is printed on purpose (D5.4: hiding a real zero is the defect being cured). Do not read its presence as instrument noise. |
| **unknown** (no snapshot row) | **ACTIONABLE — but the action is about the snapshot, not the office** | Treat the missing class as the finding. Check `snapshot_age_days` on the page header: if `STALE` is printed, the refresh defer has fired (§5, DW-1) and the action is *refresh the snapshot*, not *chase the office*. If the snapshot is fresh and the guid is still absent, the office post-dates the 2026-09-11 read — a newly-onboarded office, which is precisely where onboarding failures live. Escalate as `activating`. | The guid acquires a class on the next snapshot, **or** it is confirmed as post-snapshot onboarding and handled as `activating`. | Do not guess the class. Do not assume `unknown` means `dark` — that assumption inverts the instrument (a new office that never books would be silently forgiven). Do not act on the office's booking rate before its class is known. |
| **`***` residual** | **N/A — cannot occur** | `***` is excluded from floor evaluation (D5.3): neither "arrivals for this office" nor "bookings for this office" is defined for an aggregate over an unknown number of offices. It can never carry a `FLOOR-ZERO` verdict. It appears only as section [4]. | — | Do not evaluate it. If a `FLOOR-ZERO` row ever carries `***`, that is an **evaluator defect**, not a floor breach — file it against the build, do not investigate an office. |

#### `FLOOR-RATE` × office class

| office class | ACTIONABLE or EXPECTED SILENCE | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| **active** | **ACTIONABLE — this is the class the instrument was chartered on** | This is the founding shape: mail keeps arriving, a trickle books, the collapse is invisible at the booking plane because bookings are not zero. Open the decline path for that guid and read *what the arrivals are being declined for* (`terminal_decline` reasons, `ad_lead_gate_refused`, `booking_gate_declined`). The question is "what changed in the gate", not "is the office alive". No fragility check is needed — §4.2 shows this floor is robust to test traffic by a factor of 14 to 249 arrivals. | The rate recovers above r, **or** the decline reason is named and routed with an owner. | Never contact a client from the page. Do not re-tune `r` to silence it — ADR D1.7 binds: a threshold is the operator's, and a seat that re-tunes after a page has broken the instrument's calibration on the record. |
| **activating** | **ACTIONABLE** | Same read as active, with the onboarding question first: a partially-wired funnel can produce a trickle. Route to the onboarding owner with the decline reasons attached. | A first-class booking rate is established or the wiring gap is named. | Do not average it against mature offices. |
| **dark-at-Offer-grain** | **EXPECTED SILENCE — with one raised eyebrow** | A dark office that books at all is a class contradiction, and it is a **measured** one: guid `15caa02c` books while dark at the Offer grain (charge §7, ADR D5.2 row E4). One action: ask whether the class is stale. Do not open an incident. | The class is corrected on the next snapshot, or the contradiction is accepted and recorded as known. | Do not treat the contradiction as an instrument defect — E4 (derive class from booking history) was **rejected** precisely because the two provably disagree. |
| **unknown** | **ACTIONABLE — snapshot-first** | Same as `FLOOR-ZERO` × unknown: the missing class is the finding. Then read the rate. | As above. | Do not guess the class. |
| **`***` residual** | **N/A — cannot occur** | Excluded from evaluation (D5.3). | — | As above: a `***` row in a floor section is a build defect. |

#### `FLOOR-REFUSED` × office class — **office class does not vary the action**

| office class | disposition | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| all five, identically | **ACTIONABLE — and it is an instrument incident, not an office incident** | The page carries `query_status`, `records_scanned`, `offices_with_bookings`, `control_reason`, the window, and the literal sentence *"no floor verdict was produced for this run"*. Read `control_reason` and triage which leg failed: `records_scanned < 500` points at a wrong log group, a wrong epoch window, or a truncated result; `offices_with_bookings < 5` is the **discriminating** half and points at a mis-scoped filter or an empty interval; `query_status != Complete` points at Insights itself. Route to the platform owner. | The next 11:00Z run publishes a `FLOOR-DIGEST` with a passing control. | **Do not conclude that no office is below floor.** A refusal is not a quiet verdict — that inversion is the exact defect D2.6 was written to forbid. Do not look for an office name on this page: there is none, by construction, and its absence is correct. Do not clear it by re-running by hand and reading the output as the day's verdict. |

**Why this row matters more than it looks.** `FLOOR-REFUSED` is the only page class that can be
mistaken for good news. Every other class names a problem; this one names *the absence of an
answer*. The withheld `LastSuccessTimestamp` (D2.6) is the wire that carries the off-hours case to
the alarm plane, so a reader who ignores a refusal page will still be reached — **once the deadman
is armed at the real topic.** Until the word (§2), that wire ends in a scratch topic.

#### `DEADMAN-liveness` (prober / freshness) × office class — **office class does not vary the action**

| office class | disposition | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| all five, identically | **ACTIONABLE — the instrument itself is dark** | The evaluator has not invoked for ≥ 7200 s plus two 3600 s breaching periods (≈ 4 h). Check the EventBridge rule `module.office_floor.schedule_rule_name` is enabled, then the Lambda's own errors alarm. Restore, and confirm the gauge drops and the alarm returns OK via `ok_actions` — **both poles, the restore leg is not optional** (D2.7 Leg 1). | `OK with datapoints present` — **not** `INSUFFICIENT_DATA`. That discrimination is the one `ebi-booking-liveness-dark` failed (charge §3); an alarm sitting in INSUFFICIENT_DATA is a dark instrument wearing a green light. | Do not assume "no page today" meant "no office below floor" for the dark interval — **the floor was not evaluated at all.** Do not kill the prober to test this alarm: a MISSING gauge is treated `missing` and **does not page** (D2.3, the inverted premise). |

#### `DEADMAN-success-gap` × office class — **office class does not vary the action**

| office class | disposition | the action, within one business day | "resolved" means | do NOT |
|---|---|---|---|---|
| all five, identically | **ACTIONABLE — the instrument runs but is not trustworthy** | Two consecutive in-run control failures (≈ 2 h at the D3 cadence) have withheld `LastSuccessTimestamp`. This is `FLOOR-REFUSED` escalated by persistence: same triage, higher confidence that the cause is structural (a wrong log group, an emptied window, a permissions regression on `logs:StartQuery`). Route to the platform owner as a sustained fault. | A controlled run emits `LastSuccessTimestamp` again and the alarm returns OK. | Do not clear it by relaxing the control floors (`records_scanned ≥ 500`, `offices_with_bookings ≥ 5`). Those floors sit at ≈ 7 % and ≈ 23 % of the *smallest observed* value; loosening them to stop a page converts the instrument into a rubber stamp. |

### §1.2 Worked examples from the measured substrate — the two stall shapes vs the ten dark ones

S1.1's K3 enumerated the `FLOOR-ZERO` firing set completely: **12 members in window A, 6 in B, 3 in
C, no unexplained member in any window** (K3 PASS). Class labels there are **plane-derived proxies**
(a 30-day booking lookback), not the E2 Offer-grain class — see DW-2 in §5. The split below is the
reader's whole job on this floor, and the substrate shows it is roughly 1-in-6.

**Shape (a) — the true stall. 2 of 12 in window A. This is what the ZERO floor is FOR.**

| guid8 | window-A arrivals | 30 d arrivals | 30 d bookings | why it is a stall |
|---|---|---|---|---|
| `87bd31d7` | 33 | 106 | **12** | Books 12× in 30 days and booked **nothing** in the window. A live booking relationship that *stopped*. |
| `6b93fb76` | 24 | 58 | **4** | Books 4× in 30 days, silent in the window. Same shape, thinner history. |

Both persist into window B (12 and 11 arrivals). **Reader's action:** the `active` row of the
`FLOOR-ZERO` grid — fragility check first (both are far above the ±1 boundary: `87bd31d7` would
need 29 synthetic arrivals to go quiet, `6b93fb76` 20), then open the intake path. These two are
why the ZERO floor is **not merely a dark-office detector**.

**Shape (b) — structurally dark. 10 of 12 in window A. EXPECTED SILENCE, printed on purpose.**

| guid8 | window-A arrivals | 30 d bookings | note |
|---|---|---|---|
| `e63bbbe0` | 24 | 0 | persists A/B/C — the most persistent dark member |
| `8a9b1a84` | 15 | 0 | persists A/B/C |
| `40f86e73` | 13 | 0 | **known-DISABLED office** (ADR D5.4), persists A/B/C |
| `ea98e732` | 8 | 0 | |
| `5a19f1ad` | 7 | 0 | **no resolvable `office_name`** — renders as a guid-prefix-only row (`<guid8> —`) |
| `e5a68603` | 6 | 0 | **known MALFORMED-GUID office** (ADR D5.4) |
| `cf6ae0f2` | 6 | 0 | |
| `2b591e43` | 5 | 0 | sits **exactly at A = 5** → see §4.2 |
| `2786b72d` | 5 | 0 | sits **exactly at A = 5** → see §4.2 |
| `735416d5` | 5 | 0 | sits **exactly at A = 5** → see §4.2 |

**Reader's action:** none. These land in digest section [2] EXPECTED SILENCE **only if the E2
snapshot classes them dark**. With the snapshot unresolved (DW-2) they render `class=unknown` and
land in section [3] — which routes ten no-action rows into an actionable section. **That is the
single largest reader-load risk in this runbook**, and it is the reason DW-2 is a gate on arming,
not a nicety.

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

### §2.0 The state, verbatim

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
| variable | a **single** `page_topic_arn` — one variable, feeding **every** page path (the digest publish target passed to the Lambda's environment, and the `alarm_actions` list of the `service-lambda-scheduled` module instance, which the module shares across its freshness alarm, its self-deadman and its success-gap alarm) |
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
sitting is later in the chain and is the decision space of record; **it governs.** The ADR's
two-instance *sequencing* (metric soaks, then the alarm arms) survives intact and is unaffected by
which topic the actions point at.

### §2.2 The receipt that proves the re-point

A terraform apply is not evidence that a page reaches a reader. The re-point is proven by a
**message on the destination**, not by a plan diff:

1. Apply the one-variable change.
2. Fire a probe on the real mechanism — the cheapest honest one is
   `aws cloudwatch set-alarm-state --alarm-name autom8-ebi-booking-floor-freshness-prober-liveness
   --state-value ALARM`, then `--state-value OK`. (This proves the **action path**, explicitly not
   the detection path — D2.7 Leg 2 requires that distinction be stated in words, and it is stated
   here.)
3. **The receipt is an SNS `MessageId` published on `platform_alerts`** for that probe, captured
   with its UTC instant, plus the delivery observed on the topic — never merely the alarm's state
   transition.
4. The negative pole: the same probe fired **before** the re-point yields a `MessageId` on the
   **scratch** topic and **none** on `platform_alerts`. Two-sided, on the real channel.

Without step 3 the re-point is unproven. An `aws sns publish` from a laptop proves the topic
accepts messages; only an **alarm-driven** delivery proves the *page path* was re-pointed.

---

## §3 THE WITHHELD WORD — instant, owner, and the exact sentence

| | |
|---|---|
| **instant of withholding** | **2026-09-14**, sitting XI, S0b (`.ledge/decisions/RATIFICATION-decision-space-sitting-XI-2026-09-14.md` §1 R-168) |
| **the words given** | *"Nobody yet: build, prove, do not arm."* |
| **owner of the word** | **the operator** (Tom Tenuta). Not the seat, not the architect, not any critic. The sitting records this as a **value** ruling, and sitting XI §5 banks the operator's feedback that only value questions come to him — this is one of them. |
| **consequence already taken** | S1.7 is **REFUSED-CORRECTLY**; R1 is **NOT REALIZED** this wave; the wave's honest ceiling is *"instrument proven, reader withheld, blocker named with its instant."* |
| **what unblocks** | nothing but the word. No build, no receipt, no critic verdict substitutes for it. |

**The exact sentence the operator would say to give it** — and it must carry all four parts,
because each one is a fence that broke in a prior wave:

> **"I will read `platform_alerts` and act on an S-1 page within one business day, starting
> {DATE}; point the page paths at `platform_alerts`."**

| part | why it is load-bearing |
|---|---|
| **a named human** (*I*, or a named other) | "the team will watch it" is the hero-culture failure mode and a bus factor of zero; a page with no named reader is the silence this epoch exists to end |
| **one business day** | the charge §6 bar verbatim; it is what converts a notification into a commitment |
| **a start date** | the commitment acquires an instant, so its absence is later detectable; an undated promise cannot be missed |
| **the explicit re-point instruction** | the seat must never infer arming from enthusiasm. Sitting XI's standing fence: *"every page path stays on the scratch topic until the operator's word."* The word must say the words. |

**A partial word is a partial arming, and the split is already ruled.** R-169 and §4.2 make the
ZERO floor's smoke exposure ±1 arrival while the RATE floor is robust. If the operator wishes to
commit to the founding class only, the lawful form is:

> **"I will read and act on `FLOOR-RATE` pages within one business day, starting {DATE}; point the
> page paths at `platform_alerts`; the `FLOOR-ZERO` class stays on the scratch topic until the
> smoke-lead convention is named."**

That is buildable within the D8 digest shape (the classes are already sectioned) and it is the
shape S1.1's §6.1 sized: the smoke convention *"must be codified before the ZERO floor is armed,
and need not gate the RATE floor."* **This runbook does not choose between the two sentences.**
That is the operator's, and recording the choice as available is the whole of the seat's duty here.

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

**THE CHECK, before acting on any `FLOOR-ZERO` page.** Three questions, in order, all cheap:

1. **Is `arrivals` at or near 5?** If `arrivals ∈ {5, 6, 7}`, the verdict may rest on one or two
   lines. Treat it as provisional until step 2.
2. **Did anyone run a smoke test through this office in the window?** There is no field to ask, so
   **ask the human.** This is the un-automatable step and it exists only because the convention is
   uncodified (DW-3). Record the answer on the page thread either way — that record is the
   substrate the eventual convention will be built from.
3. **Does the `day N` counter say 1?** A brand-new `FLOOR-ZERO` crossing at `arrivals = 5` is the
   highest-prior smoke artefact in the whole instrument. A day-4+ standing zero at `arrivals = 5`
   is far more likely to be real: smoke traffic does not usually persist for four consecutive
   windows.

**No such check is required before acting on a `FLOOR-RATE` page.** The arithmetic says the founding
class cannot be created or destroyed by test traffic. A reader who applies the fragility check to
a RATE page is spending attention the instrument does not need — and, worse, is rehearsing a habit
of doubting the one class that is robust.

**The cure, and its owner.** The durable fix is a reserved test office or a marker field (packet
F5-4); the interim fix is the operator **naming** the convention (F5-1). R-169 binds it: the
convention is codified **before any arming**. Per S1.1 §6.1 the binding is sharpest on the ZERO
floor. UV-P-1 stays open with the **operator** as owner. See DW-3.

---

## §5 DEFER-WATCH MANIFEST

Everything this runbook depends on that does not yet exist. Per `defer-watch-manifest`: each item
carries an owner, a refutable watch-trigger, and an escalation path. **No row is `NO WATCHER`** —
the sitting's own rule.

| id | item | deferral rationale | watch-trigger (refutable) | owner | escalation | blocks arming? |
|---|---|---|---|---|---|---|
| **DW-1** | **The E2 class snapshot is not in this repo.** ADR D5.1 rules a build-time constant sourced from `READ-offer-activity-sizing-2026-09-11`; S1.1 recorded that artifact as present in **neither** the working tree nor `origin/main` (`git ls-tree -r --name-only origin/main` grepped for `offer-activity-sizing` → empty). Without it, §1.1's entire office-class axis is unpopulated. | The sizing read was taken 2026-09-11 and cited by the charge §7; the artifact was never landed to a ref. | `git ls-tree -r --name-only origin/main \| grep offer-activity-sizing` returns non-empty **AND** the evaluator's checked-in data file carries `snapshot_date = 2026-09-11`. | **platform-engineer (S1.3)**; source custody with the operator/prior seat | If unresolvable at S1.3, the builder **recedes to the operator** — do not substitute the plane-derived proxy (that is E4, explicitly rejected by ADR D5.2). | **YES** — see DW-2 |
| **DW-2** | **The class labels in S1.1's K3 are plane-derived proxies, not the Offer-grain class.** They discharge K3's "no unexplained member" test and are **not** a substitute for E2 at build time. | S1.1 had no access to the snapshot (DW-1) and said so in its own UV-P rather than passing the proxy off as the class. | Any digest renders ≥ 1 row with `class` ∈ {`active`,`activating`,`inactive`,`dark`} sourced from the checked-in snapshot file, not from booking history. | **platform-engineer (S1.3)** | If S-1 is armed while classes are proxies, **ten of twelve no-action rows route into section [1]/[3] instead of [2]** and the reader's first week is 83 % noise on the ZERO floor. Escalate to the operator before any arming. | **YES** |
| **DW-3** | **The smoke-lead convention (R-169 / F5-1) is unnamed.** VERIFIED-ABSENT in code at both repos; no marker, no reserved guid, no predicate. §4.2 step 2 is therefore a human question with no instrument behind it. | The operator ruled the current practice (real offices, no marker) and reserved the convention to himself. | The operator names the convention **and** it is codified in a ref-resolvable artifact. Durable form = F5-4 reserved office. | **operator** (UV-P-1 owner, per sitting XI §3) | R-169 binds: codified **before any arming**. Per S1.1 §6.1 the binding is strict for `FLOOR-ZERO` and not required for `FLOOR-RATE` — which is exactly the partial-word shape offered in §3. | **YES for `FLOOR-ZERO`; NO for `FLOOR-RATE`** |
| **DW-4** | **The consumer commitment itself** (§2, §3). | R-168, recorded with its instant. | The operator speaks a §3 sentence, on the record, with a start date. | **operator** | Nothing else unblocks it. S1.7 stays REFUSED-CORRECTLY; the handoff says so in line one. | **YES — this is the arming gate** |
| **DW-5** | **`office_floor.tf` / `page_topic_arn` do not exist yet** (the §2.1 UV-P). | S1.2 is record-only; the build is S1.3. | The file exists at `autom8y:terraform/services/email-booking-intake/office_floor.tf` and exposes exactly one `page_topic_arn` feeding both the digest target and the module's `alarm_actions`. | **platform-engineer (S1.3)** | If the builder exposes **two** topic variables (or hard-codes either path), §2.1's "one change" promise is void and this runbook's §2 must be re-authored before arming. | **YES** |
| **DW-6** | **The snapshot-refresh cycle** (ADR D5.1 rule 3 / §12 row 1). | Deliberately self-surfacing: the page emits its own staleness. | `snapshot_age_days > 30` appears on any page (renders `STALE` on every row). | **the S-1 consumer (the operator)**, via this runbook's §1.1 `unknown` row; **watcher = the page itself** | Refresh = a read-only re-run of the sizing read. If the page is unread (the current state), this watcher is **also dark** — the defer is only self-surfacing once DW-4 closes. | no (but see note) |
| **DW-7** | **`contente_booking_allowlist_suppressed` is unclassified.** S1.1 FACT-3 found 4 window-A lines of an office-bearing event that ADR D1.1's terminal set does not enumerate. | Raised as a UV-P by S1.1 rather than silently folded into the unit. | The builder either adds it to the terminal set with a ruling, or records it as deliberately excluded with a reason. | **platform-engineer (S1.3)**, escalating to the architect | Silent inclusion changes the arrival unit without a ruling — an ADR D1 breach. Silent exclusion is acceptable **only if stated**. | no |
| **DW-8** | **The `FLOOR-REFUSED` and `DEADMAN-*` page bodies are specified but unrendered.** §1.1's triage rows assume the fields D2.6 lists (`query_status`, `records_scanned`, `offices_with_bookings`, `control_reason`, window, the literal refusal sentence) are actually on the page. | The evaluator is unbuilt. | S1.4's `FLOOR-REFUSED` probe receipt shows all six elements present in the published body. | **chaos-engineer (S1.4)** | If any field is missing, §1.1's `FLOOR-REFUSED` row is unexecutable and this runbook must be re-authored before arming. | **YES** |

**Note on DW-6.** A self-surfacing defer whose surface is an unread page is not self-surfacing.
This is the general shape of every watcher in this wave: **R-168 makes the page the weakest link in
every chain that ends at it.** That is not a defect in the design; it is the accurate consequence
of an unarmed instrument, and it is why the wave's exit line says the reader is withheld rather
than saying the instrument is live.

---

## §6 ANTI-THEATER SELF-CHECK

| check | result |
|---|---|
| Does any action item target a human's memory rather than a system? | §4.2 step 2 does — **knowingly**, and it is filed as DW-3 with the operator as owner and a durable cure named (F5-4 reserved office). It is labelled *"the un-automatable step [that] exists only because the convention is uncodified"*, not presented as a practice. |
| Does the runbook claim S-1 is live, armed, or read? | **No.** The header, §2.0, §3 and DW-4 each state the opposite. The word `WITHHELD` is reproduced verbatim as the sitting wrote it. |
| Does any cell say "investigate" or "be careful" without a named action? | No. Every cell names what to open, what to ask, what "resolved" means, and one or more prohibitions. |
| Is any claim about a not-yet-built primitive asserted as present-tense fact? | The `office_floor.tf` / `page_topic_arn` contract is the only one, and it carries a UV-P label (§2.1) under SVR AP-4 plus a defer row (DW-5). |
| Are the fences held? | guid8 only throughout (every guid reproduced from S1.1 is already an 8-char prefix); **no office name appears**; **no phone digits appear**; no page path was repointed; nothing was merged or armed. |
| Were governance reads taken from a named ref? | Yes — `origin/main` for sitting XI, `origin/sre/s1-1-observe-20260914T040422` for S1.1, both via `git show "${REF}:path"`. The ref is named in §0 and in the frontmatter. |
| Contributing factors, not a root cause? | The instrument's own failure surface is decomposed into five page classes and eight defer rows; no single "root cause" framing appears. The `FLOOR-REFUSED` row exists precisely because the absence-of-an-answer is a distinct contributing factor from any office's behaviour. |

**Evidence grade: MODERATE** (`self-ref-evidence-grade-rule` ceiling). The runbook's subject is an
instrument that has not run. Its substrate (S1.1's K1–K5, the ADR's parameters, the sitting's
rulings) is measured and ref-anchored; its own operational claims — that these actions are the right
actions — are **untested by construction** and will remain so until a reader exists. The honest
upgrade path is not a better runbook; it is DW-4.

**The acid test.** *If the founding silence happens again, does this runbook prevent a repeat?*
**Not yet — and the reason is named with its instant.** The instrument would detect it (K1: the
founding office fires the RATE floor in all three windows). The digest would name the office. And
the page would land on a scratch topic that nobody reads. The gap between "detected" and
"prevented" is exactly one sentence from one person (§3), and this runbook's whole purpose is to
make that sentence cheap to say and impossible to say by accident.
