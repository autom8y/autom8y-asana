---
type: review
status: draft
artifact_id: REPORT-exec-state-of-work-2026-08-13
initiative: exec-insight-delivery
audience: CEO + cofounder (delivery is operator-performed; this document does not send itself)
register: orientation — per operator ruling R-16 this document keeps every decision open; it argues for nothing
lifecycle: one-off (the recurring insights readout is a separate artifact with its own cadence)
date: 2026-08-13
---

# The Asana insight system — where it stands

*One-off state-of-work readout. A separate, recurring report of the business
insights themselves will follow on its own schedule. This document is about the
system that will produce it: what it does, what we learned building it, what it
can honestly tell you today, and what is broken.*

---

## The one-paragraph version

We run our offers pipeline on an Asana board, and we built a system that checks
that board against reality on a fixed schedule and reports what it finds. The
most important thing we discovered while building it is that several of our own
measurements were quietly answering a different question than the one we were
asking — a clock that said "the data is fresh" when it actually meant "the
server restarted recently," an alarm that said "all clear" because it was
looking at a reading nine days old. We rebuilt the system so it can tell the
difference between **"we checked, and it was right"** and **"the process ran."**
The direct consequence: it now refuses to vouch for data it cannot verify, and
it says so out loud rather than guessing. That refusal is currently visible six
times a day in our Slack channel, and it is the system working as designed — not
an outage.

---

## What it does today, concretely

- Every four hours, it attempts a full reconciliation of the offers board.
- Before reporting anything, it checks whether the data it holds can be
  verified as current. If it cannot, it **stops and posts a notice saying
  exactly why**, rather than publishing numbers it cannot stand behind.
- That check has run on schedule, without exception, every cycle we measured —
  we audited every run over a recent 24-hour window and each one behaved
  identically and correctly.
- The channel it posts to is live and delivering — we verified the deliveries
  in the logs, not by assumption.

Right now it is in the refusing state most of the time. That is honest: the
verification machinery that would let it vouch for the data is designed,
approved, and partly built, but the final pieces have not shipped. Until they
do, "we cannot verify this yet" **is** the correct report.

## What we learned building it — and why it matters beyond this system

Four separate times, we found a number that looked like a health signal but was
measuring something else. Each one had the same shape: **one quantity being
used to answer two different questions.** The age of a cache entry read as the
age of the data. A build timestamp read as evidence of fresh content. An alarm
that inferred "the pipeline is fine" from a stale datapoint.

None of these were sloppy work — each was reasonable in isolation. The failure
mode is structural, and we now have a working defense against it: every number
the system publishes must be able to say *what it measures, how it was
verified, and in which direction it errs when it errs*. Numbers that cannot
answer those questions are withheld, visibly, instead of shipped.

We then applied that same standard to our own conclusions, using independent
reviewers instructed to attack rather than confirm. **Several of our own claims
failed and were withdrawn** — including two of the three reports we initially
believed were ready to publish. The one that survived was the one attacked
hardest. We consider the withdrawals a feature of the process, not an
embarrassment of it: every error we found was caught by a second reader going
one step past where the first one stopped, and that discipline is now built
into how this work is reviewed.

## What it can honestly tell you today

**One report, today, without further building**: which sections of the offers
board have gone longest without any edit — quiet corners, per section, with
the measurement's age stated alongside it. This survives our publication bar
because the underlying timestamp is Asana's own, so a system failure on our
side can only *overstate* quiet time, never manufacture activity. A wrong
answer errs in the safe direction, and the report says how stale it might be.

**Two more were candidates and were withdrawn** — one measuring how long
offers sit in the launch pipeline, one summarizing weekend movement. Both
turned out to depend on a data source that, on inspection, fills gaps in its
history with a guess (see "What is broken"). Until the guessed entries are
distinguishable from real ones, those reports could state as fact things we
never observed. They return when that is fixed; the fix is understood and
scoped.

This is the deliberate trade: **fewer numbers, each one defensible.** The
recurring readout will start with what clears the bar and grow as more does.

## What is broken — plainly, with honest severity

Three findings, all discovered by this work, all now routed to owners. None
involves customer data exposure, and none is a *known* active incident — but for
finding 2 in particular, how often it actually fires is something we have not
measured, and we mark that explicitly rather than assume it is zero.

1. **A background process that keeps our data warm has been silently starving
   most of the data it serves.** It refreshes data types in a fixed order with
   a time budget, and the budget runs out partway through the list — every
   run, for at least the last two weeks. Twelve of sixteen data types,
   including offers, have received no refresh in that window. Nothing alerted,
   because the process reports "success" when it completes *any* work. This is
   the widest finding and it extends beyond this project; it is being routed
   to the platform team rather than patched locally.

2. **A query feature can report offers as having "moved" when they were merely
   created.** When an offer's history is missing, the system fills the gap with
   a guess, and the guess is indistinguishable from a real observation in the
   output. Per finding 1 that history is currently missing for what we *infer*
   to be effectively all offers — an inference, not a count; we did not read
   every entry. Two-sided, honestly: the flaw itself is real and present as a
   correctness defect, but *how often it is actually hit* depends on how often
   this query is run, which we have not measured. The fix is one change —
   guessed entries must be labeled as guessed everywhere they appear — and it is
   scoped and routed.

3. **An internal service-to-service door checks identity but not
   permission.** Any service inside our fleet that can authenticate can reach
   write operations that should require a specific grant. We have found no
   evidence it has been misused; whether the endpoint is reachable from outside
   our own network we have not yet verified — it sits behind our platform load
   balancer, but we have not confirmed that balancer is internal-only; and a
   standing operational rule currently prevents the writes in question — but
   that rule is procedure, not software. Routed to a security review.

We found all three ourselves, with the same verification discipline described
above. We'd rather report them than have them found later.

## What we are confident of, and what we are not

**Verified directly** (logs, live systems, re-checked by a second reviewer):
the four-hourly check runs and refuses correctly; the Slack deliveries happen;
the warming process starves as described (audited across 324 runs); the one
publishable report's data path.

**Inferred but not enumerated**: that the offer history cache is completely
empty (we proved nothing writes to it and its entries expire in minutes; we
did not read every key). One authenticated call would convert this from
inference to measurement.

**Not yet known**: whether anyone on the offers team wants or reads
board-level reporting — we have deliberately not asked yet, and this report
does not assume the answer. How often the "moved-vs-created" query feature
(finding 2) is actually run — its real-world exposure is a function of traffic
we have not measured. Whether the service-to-service endpoint (finding 3) is
reachable from outside our network. And how often the recurring readout should
arrive — that is a decision, not a discovery.

## What happens next, as currently planned

- The **recurring insights readout** starts with the one report that clears
  the bar, on a cadence to be set, delivered automatically to Slack with no
  human assembling it.
- The **verification upgrade** that lets the system vouch for data again has
  one approval gate remaining before build; the preceding gates cleared this
  week, including a live audit that found the underlying tracking healthy to
  within minutes.
- The **three findings above** proceed with their owners, independently of the
  readout work.

## What this document deliberately does not do

It does not recommend whether to invest further, tell you to trust or distrust
the numbers, or rank the problems. Those are your calls, and the system this
describes was rebuilt around exactly that principle — report what is known,
state how it is known, and leave the decision where it belongs. If any section
here reads as steering, that is a defect in the document; say so and it will
be corrected.
