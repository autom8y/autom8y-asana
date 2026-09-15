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
python3 scripts/read_the_name/arm_observe.py lookup <guid8> --print-name
```

- One name returned means it is resolved.
- No names, or several, means do not guess: ask the operator.
- No AWS access at all: ask the operator.

Keep the name off the email thread, Slack, tickets and PRs, and write the guid8 there instead. The raw log line behind this lookup also carries the clinic's phone number. The command never shows it; do not go and look.

**Step 2 — for a ZERO row, check the lead-match share *before anyone contacts the clinic*.**

```
python3 scripts/read_the_name/arm_observe.py C <guid8>
```

If most of the office's arrivals failed with `LeadMatchError` and the failures share **one From domain** (a parsed email header, not a verified sender), the zero is our matcher failing, not the clinic. **Do not call the clinic**; route it to the platform owner.

- Measured today: `8a9b1a84` failed 8 of 9 and `e63bbbe0` failed 3 of 3, both sharing the same From domain, so do not call either.
- `40f86e73` and `2786b72d` had no lead-match failures: they are genuine zeros.

One more check: a `day 1` ZERO row with only 5–7 arrivals may come from a single unmarked test lead (runbook §4.2). Ask the operator whether a smoke test ran.

**Step 3 — act according to the runbook**, within one business day: §1.1 covers page class × office class, and §1.1.1 covers an empty digest. Never contact a client from the page itself.

**Cadence.** One digest a day. The founding office `ccb52f4c` sits right at the RATE floor: it was on it in 27 of 43 hourly checks over the last 48 hours, and just above it in the rest. Expect it on most days, and when it appears, it needs action. A day it is missing is arithmetic, not a fix.

**No digest by about 12:00 UTC is a signal, not a quiet day.** The evaluator may have stopped. Its own alarm goes red only at roughly the fourth missed hourly run, so you may be the first to notice. Tell the operator.

**What else is on this channel.** You are joining a busy stream: about 30 messages a day (28–35 a day over 09-11..09-14), from 347 alarms across the whole platform. 46 of those alarms were in ALARM at the time of writing; they are standing conditions, and most are not yours.

- **Yours:** the daily digest, plus alarms named `autom8-ebi-booking-floor-*` or `autom8-email-booking-intake-office-floor-*`. Those alarms mean the S-1 instrument itself is dark or failing, and they route here only after the arm.
- **Not yours:** everything else.

`[UV-P: the digest's exact email subject and Slack rendering | METHOD: read the first 11:27Z page after the re-point | REASON: no evaluator digest has reached this channel yet; filter on it once seen]`

**What nobody can see.** Nothing records that you read the page. If you stop reading, the silence is recorded nowhere. Your dated acknowledgement on the day-1 page thread (guid8 only) is the only observer the arming receipt can cite.

**Owner of everything above:** the operator (Tom Tenuta), until the reader role is re-seated on the record (runbook §1.1, C-5).
