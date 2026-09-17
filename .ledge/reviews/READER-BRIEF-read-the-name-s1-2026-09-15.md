---
type: review
artifact_kind: reader-brief
initiative: read-the-name
sprint: S1.7 pre-arm paper (P3b)
rite: sre
station: incident-commander
created: 2026-09-15
for: the reader the operator names for the S-1 page
governing_runbook: .ledge/reviews/RUNBOOK-read-the-name-s1-2026-09-14.md (§1–§7; §7 is the 2026-09-15 amendment)
arming_receipt: .ledge/reviews/ARMING-RECEIPT-read-the-name-s1-2026-09-21.md
evidence_grade: MODERATE
arming_state: NOT ARMED — this brief arms nothing
---

# READER BRIEF — the S-1 office booking-floor page, on one page

**What it is.** Once a day, at about 11:27 UTC, the S-1 evaluator publishes a digest to `autom8y-platform-alerts`. It reaches you by **email** and in **Slack `#platform-alerts`**. The digest lists offices whose email-booking funnel looks broken over the last 3 days:

- **ZERO**: at least 5 arrivals and **no bookings**.
- **RATE**: at least 20 arrivals, at least one booking, and a booking rate under 2.5 %.
- **REFUSED**: the evaluator's own check failed, so **there is no verdict for that run**. It means *we don't know*, never *all clear*.

Each row also carries:

- `day N`: how many days running the office has been below the floor.
- `last_booking_age_days`: the key that decides what to do. **30 or less** means the office books and has stopped, so act, whatever its class.
- a class label: context only, never a reason to stand down.

**The page names each office by an 8-character guid prefix only**, for example `8a9b1a84`. There is no clinic name and no phone on the page. That is deliberate, and it must stay true of anything you write back.

**Step 1 — find out which clinic it is, off the page.** From an autom8y-asana checkout, with an AWS session:

```
python3 .ledge/reviews/read-the-name/arm_observe.py lookup <guid8> --print-name
```

- One name returned means it is resolved.
- No names, or several, means do not guess: ask the operator.
- No AWS access at all: ask the operator.

Keep the name off the email thread, Slack, tickets and PRs, and write the guid8 there instead. The raw log line behind this lookup also carries the clinic's phone number. The command never shows it; do not go and look.

**Step 2 — for a ZERO row, find out *why* it is zero, before anyone contacts the clinic.**

```
python3 .ledge/reviews/read-the-name/arm_observe.py C <guid8>
```

It prints one of four verdicts. Two of them look the same from the page and mean opposite things, which is the whole reason this step exists:

- **OUR MATCHER** — the office's failures sat on a **partial lead read**: one of the two status legs was lost and we scored only the survivors, so we never saw the candidate set whole. This one is our defect. **Do not call the clinic**; route it to the platform owner.
- **NOT AD-ORIGINATED** — the failures are dominated by one sender and **every read was complete**. We saw the whole set and there was no ad-originated lead to bind, because these patients never came from our funnel. This is the product working as ruled. **Do not call the clinic** about a booking gap either — and **do not report it as our bug**, because it is not one.
- **MIXED** — some traces partial, some complete. Part of this zero is ours and part is not. Do not call until the platform owner has split it.
- **office-side** — few or no match failures. This is a genuine not-booking signal. Work the runbook §1.1 cell.

Measured 2026-09-15, and note that the two zero-floor offices land in the *second* group, not the first: `8a9b1a84` (8 of 9 arrivals failed) and `e63bbbe0` (3 of 3) are **NOT AD-ORIGINATED** — one sender, and **0 of their 8 and 0 of their 3 failure traces sat on a partial read**. Meanwhile `79be1b75` (4 of 4 partial) and the founding office `ccb52f4c` (2 of 3 partial) **are** ours. `40f86e73` is a genuine zero.

**Why the distinction is worth a command.** A sentence that said "arrivals dominated by one sender means our matcher is failing" would be wrong for both of the offices you are most likely to see, and it would have you report our product working correctly as a defect. Read completeness is the discriminator, and nothing on the page shows it.

One more check: a `day 1` ZERO row with only 5–7 arrivals may come from a single unmarked test lead (runbook §4.2). Ask the operator whether a smoke test ran.

**Step 3 — act according to the runbook**, within one business day: §1.1 covers page class × office class, and §1.1.1 covers an empty digest. Never contact a client from the page itself.

**Cadence.** One digest a day. The founding office `ccb52f4c` sits right at the RATE floor — on it in 21 of 40 hourly checks over 40 hours, just above it in the rest — **and, corrected 2026-09-16, that reading is a plumbing shape, not the clinic's behaviour.** Every one of its ~130 arrivals over 3 days was `unknown_loud`: mail the classifier could not recognise as any intake shape, arriving by relay from ~25 senders. Its real activity is ~6 bookings by its native path, and its "rate" is those 6 ÷ a forwarded inbox. **When this office appears on the page, do not treat it as a clinic that stopped booking.** Do not call it about a booking gap. Route it to the platform owner as the known relay-sink case (arming receipt E-6), and note that an EBI park rule for exactly this mail is scheduled; depending on that rule's emission shape the office may leave the RATE floor entirely at the deploy, which is a measurement change and not a recovery. A day it is missing is arithmetic, not a fix.

**How fragile that reading is, measured 2026-09-17T04:45Z — read this before acting on a firing.** In the
live 3-day window the founding office sits at **arrivals 181 · bookings 5 · rate 2.76 %**, against a RATE floor
of **2.50 %**. **The margin is 0.26 percentage points, which is one event wide:**

```
lose ONE booking      4 / 181 = 2.21 %   -> the floor FIRES
gain 19 arrivals      5 / 200 = 2.50 %   -> the floor FIRES
```

**So a firing on this office is more likely a one-booking fluctuation than anything about the clinic.** Do not
read a firing as deterioration and do not read an absence as recovery; at this margin both are noise until
something else corroborates them. Two specific things can move it without the clinic changing at all:
a change that alters how its mail is parked shifts the **arrivals**, and its bookings are **native** (measured
2026-09-17: 0 on the contente path, 10 native over 30 days), so anything touching the contente path moves the
**rate's numerator not at all** — if someone tells you a contente change explains a firing here, it does not.

**A live case, 2026-09-17T04:50Z, showing how the margin can APPEAR to move when it has not.** A neighbouring
lane measured four new parks carrying this office's handle and reported the arrivals as 181 → 185, the rate as
2.76 % → 2.70 %, and the margin as 0.26 → 0.20 points. **Checked against the evaluator's own projection, the
margin did not move at all:**

```
4 lines  park_kind=ops     -> evaluator office_guid = ***            NOT this office's count
2 lines  park_kind=review  -> evaluator office_guid = ccb52f4c-***   counted
ccb52f4c: arrivals 181 · bookings 5 · rate 2.76 % · margin +0.26  -- UNCHANGED
```

**Both readings are honest and they disagree because they are about different things.** Those four mails really
are this office's — the neighbouring lane read the handle correctly. **But the evaluator counts on a different
field, so they land in the unattributed residual instead** (SOAK §3e). **When someone tells you this office's
arrivals moved, ask which field they counted on before you act.**

**One more trap on this office specifically.** Its allowlist membership is resolved at **cold start**, not per
request, so a configuration change with no accompanying deploy takes effect **per container** as environments
recycle — there is no single instant to point at. If a firing coincides with such a change, the before and
after are not clean, and the page should say so rather than pick a time.

**No digest by about 12:00 UTC is a signal, not a quiet day.** The evaluator may have stopped. Its own alarm goes red only at roughly the fourth missed hourly run, so you may be the first to notice. Tell the operator.

**What else is on this channel.** You are joining a busy stream: about 30 messages a day (28–35 a day over 09-11..09-14), from 347 alarms across the whole platform. 46 of those alarms were in ALARM at the time of writing; they are standing conditions, and most are not yours.

- **Yours:** the daily digest, plus alarms named `autom8-ebi-booking-floor-*` or `autom8-email-booking-intake-office-floor-*`. Those alarms mean the S-1 instrument itself is dark or failing, and they route here only after the arm.
- **Not yours:** everything else.

`[UV-P: the digest's exact email subject and Slack rendering | METHOD: read the first 11:27Z page after the re-point | REASON: no evaluator digest has reached this channel yet; filter on it once seen]`

**What nobody can see.** Nothing records that you read the page. If you stop reading, the silence is recorded nowhere. Your dated acknowledgement on the day-1 page thread (guid8 only) is the only observer the arming receipt can cite.

**Owner of everything above:** the operator (Tom Tenuta), until the reader role is re-seated on the record (runbook §1.1, C-5).
