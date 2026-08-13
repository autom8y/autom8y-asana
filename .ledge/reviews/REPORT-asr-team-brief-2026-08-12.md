---
type: review
status: draft
artifact_id: REPORT-asr-team-brief-2026-08-12
title: "Account-health checker — team brief #1: what it does for you, what we learned about the board, and why the report is paused"
audience: offers/account team (Asana-facing; non-engineering)
date: 2026-08-12
author: releaser rite (operator-commissioned team brief)
sources: see Appendix (operator-only artifact pointers)
evidence_note: >
  Every number in this brief is a real measurement from 29 days of production
  records (2026-07-14 to 2026-08-12). Where a number is exact, it is stated
  exactly. Nothing is graded above its evidence.
---

# Account-health checker — team brief

*The first regular brief from the automation side to the team that works the
offers board. Written for people who live in Asana, not in code.*

---

## 1. TL;DR for the team

- **The automated account-health report in #account-health has been paused since Monday evening (Aug 11).** The last full report is from **Aug 11, 16:01 UTC**. It stopped itself on purpose: a safety check we recently made more honest is doing exactly what it was told to do while we rebuild it. **Your data in Asana is complete and unaffected.**
- **Nothing you did caused this, and you don't need to change how you work.** The safety check assumed every part of the board gets edited every hour. We measured 29 days of real activity and learned that the launch-pipeline sections are worked about once per evening and not at all on weekends — a rhythm the old check could never pass.
- **While it's paused:** no new account-health snapshots are being taken. Each missed run is a permanent gap in the history (it won't be backfilled), but the full current picture comes back on the first good run after the fix.
- **The fix:** a rebuilt checker that passes whenever we have recently *confirmed the data is complete and correct* — instead of requiring that somebody *edited a task* recently. It will stop confusing "nobody touched the board this weekend" with "the data is broken." Rollout is staged and careful, on a weeks scale; we are deliberately not promising a date.
- **A bonus from the measurement:** we now have a precise picture of how the board is actually worked (roughly hourly on the optimization side, an evening batch on the launch side, quiet weekends) — and confirmation that we're running at about **15x headroom** below the system's capacity limits.

---

## 2. What our account-health checker does for you

Every **four hours, around the clock**, an automated job cross-checks three
things for every account and posts what it finds to **#account-health**. An
"account" here means one **office phone number + vertical** combination. The
three things it lines up:

1. **The offer task in Asana** — which section it sits in, and its custom fields (`weekly_ad_spend`, `offer_id`, …).
2. **The ad campaign** — whether one is actually running, and with what budget.
3. **The billing records** — payments and invoices for that account.

For each account it first tells you **which of the three it could find** (for
example "billing + campaign" means it found payments and a running campaign but
no offer task). Then it grades the account. Healthy accounts don't appear at
all — the report only shows what needs eyes, worst first.

### The main verdicts, in board terms

| What you see | What it means | What to do |
|---|---|---|
| **Ghost campaign** | A campaign is **spending money**, but there is no offer task for it in an ACTIVE section — either no task exists at all, or the task sits in an inactive section. | Decide which side is right: stop the campaign, or create/move the offer task so the board reflects reality. |
| **Missing campaign** | An offer task sits in an **ACTIVE** section, but **no campaign is running**. The board says the client is live; the ads say otherwise. | Highest urgency after billing issues — get the campaign running, or move the task out of ACTIVE if it shouldn't be there. |
| **Transitional** | The offer task is in an **ACTIVATING / launch-pipeline** section and has no campaign yet. | Normally nothing — this is what mid-launch looks like. Worth a look only if it lingers for a long time. |
| **Budget drift** | The campaign's weekly budget and the task's **`weekly_ad_spend`** field differ by **5–20%**. | Review when convenient; align whichever side is wrong. |
| **Budget mismatch** | They differ by **more than 20%**. | Fix promptly — either the campaign budget or the `weekly_ad_spend` field is materially wrong. |
| **Budget unavailable** | The checker **couldn't grade** the budget — usually `weekly_ad_spend` is empty or zero on the task, or the campaign's budget data is incomplete. | Fill in `weekly_ad_spend` on the offer task. "Couldn't grade" is counted separately from "graded clean" — it never hides in the all-clear. |

### Other flags you may see

| What you see | What it means | What to do |
|---|---|---|
| **Paying, no ads** | The client's payments are arriving but **no ads ran at all**. Rendered at the very top — this is the trust-critical case. | Investigate immediately. |
| **Ads running, no payment** | We're spending on the account but **nothing has been collected** and there are no invoices. | Check billing setup for the account. |
| **Overbilled / Underbilled** | What was collected diverges from what the spend says it should be (beyond a 10% / 25% tolerance). | Route to billing review. |
| **Stale account** (advisory) | No ad activity and the last payment is over 14 days old. | Awareness only — shown under an advisory group, never as a critical item. |
| **Hollow / Barren campaign** | The campaign exists but is an empty shell — no ad sets inside it, or ad sets with no ads. Nothing can actually deliver. | Open the campaign and fill in what's missing. |
| **Three-way divergence** | Actual spend, collected payments, and the planned weekly budget don't agree with each other (beyond 10%). | Triage before acting — figure out which of the three numbers is the true one. |

Two reading tips:

- **The summary counts at the top of each report are always complete.** The per-account list below them can be cut off by the chat platform's message-size limit (the report marks this with a scissors note when it happens). If a count says 12 and you see 9, trust the count and ask us for the complete record.
- **One roll-up line, not many repeats:** accounts whose *only* issue is "campaign spending with no active offer + empty campaign shell" are collapsed into a single summary line (the enrollment-condition group), because they're tracked centrally by the enrollment program rather than being individual work items for this team.

---

## 3. What we learned about how the team actually works the board

To rebuild the safety check properly, we measured **29 days** (July 14 – Aug 12)
of real edit activity on the offers project — 175 four-hourly check-ins,
reconstructed from more than 7,000 recorded observations. This is offered as
**observation, not critique**: the board's rhythm is the team's rhythm, and the
automation has to fit it — not the other way round.

**The board has two halves with two completely different rhythms.**

- **The optimization side** (ACTIVE, OPTIMIZE – Human Review, STAGED, and their neighbors) moves **roughly every hour during the business day**. Over 29 days it moved forward 92 times, typically about 1.1 hours apart.
- **The launch pipeline** (NEW LAUNCH REVIEW and the other ACTIVATING sections) is worked as an **evening batch**: touched roughly **once per business evening, between about 20:00 and 23:00 UTC** — 26 times in 29 days, typically about 21 hours apart.
- **Weekends are fully quiet on the launch side: 0 edits across all 4 consecutive weekends** in the window. The optimization side gets occasional weekend touches (we saw a Sunday-afternoon edit), but mostly rests too.
- **The longest quiet stretches on the launch side ran 4–5 days** (the longest cleanly-measured one: 93 hours, Friday through Monday evening).
- **The Monday-morning effect:** because the optimization side sometimes moves on the weekend while the launch side never does, the two halves of the board are **furthest apart on Monday morning** — we measured the gap reaching **3.7 days** at its widest. If something reads the launch pipeline first thing Monday, it is reading Thursday-or-Friday's state, and that is *normal*, not a fault.

What this says about the workflow, plainly: **launching is an end-of-day
activity; optimizing is an all-day activity.** That's a coherent way to work a
board. It just means any automation that assumes "everything is edited hourly"
will be wrong about half the board most of the time — which is precisely what
we found, and precisely why the safety check is being rebuilt (Section 5).

One capacity note while we were in there: the checker reads the offer lists
with a **1,000-row limit per status group**. Today's counts are about **67
active and 48 activating — roughly 15x headroom**. No action needed; we're
adding an early-warning trend so growth can never silently reach the ceiling
(Section 5, improvement 3).

---

## 4. Current state: why the automated report is paused, and what you can and can't rely on right now

**What happened.** The checker has a safety gate: before grading accounts, it
verifies the offer data it's about to grade is fresh, and if not, it stops
rather than publish a report built on questionable data. On the evening of
**Aug 11** we corrected what that gate measures. It used to look at an internal
technical timestamp that could read "fresh" even when the underlying data was
old — an honesty problem. It now measures the real thing: **when someone last
actually edited a task** in each of the section groups it grades — and it
requires that to be within the **last hour, in both halves of the board, at
every run**.

You can see the collision immediately from Section 3: the launch pipeline is
touched once an evening and never on weekends. Against the team's real rhythm,
the one-hour bar is unmeetable — we replayed all 29 measured days against it
and it would have passed **0 of 175** runs (the board was inside the bar for a
total of about 39 minutes across the entire 29 days). And there is no number
that fixes this: any bar loose enough to fit the weekend rhythm (about two full
days) would be too loose to catch a genuinely stuck data feed, which is the
whole reason the gate exists.

**So the gate is doing its job — strictly, on a bar that turned out to measure
the wrong thing.** The runs still fire every four hours, stop at the gate, and
say so honestly instead of publishing. This is a **deliberate, ruled interim
state**: the decision was made to accept honest stops rather than loosen the
check into meaninglessness or quietly fake freshness, until the rebuilt gate
lands.

**What you CAN rely on right now:**

- **The data itself is complete and being served correctly.** Every single check-in confirms the full offer lists are coming through intact (68 of 68 active, 48 of 48 activating, on every run). The Asana board, the sync behind it, and everything else that reads the offer data are unaffected.
- The last **full, trustworthy** account-health picture is the one posted **Aug 11 at 16:01 UTC**. Anything in it was true as of then.
- The checker is not broken or crashed — it runs on schedule and stops itself on purpose. In #account-health you'll see it report that it stopped at its safety check instead of posting the usual account list.

**What you CAN'T rely on right now:**

- **No new account-health snapshots.** A ghost campaign or budget mismatch that appears today will not be flagged automatically until the report resumes — if something needs checking in the meantime, check it by hand or ask us to pull it.
- **The history will have holes.** Each skipped run is a window with no snapshot, and those windows are not backfilled later. The *current* state, however, recovers completely on the first good run — nothing about "now" is lost, only the play-by-play of the paused period.

**The return path:** the rebuilt checker (Section 5) is being built in careful
stages — several invisible steps first, then one small, reversible switch, then
a **14-day observation period** before we declare it done. Think **weeks, not
days**; we are deliberately not promising a date, because the ruling was to do
this properly rather than quickly.

---

## 5. What's coming

**The rebuilt checker, in one paragraph.** Instead of asking *"has someone
edited a task in the last hour?"*, the new safety gate will ask *"have we
recently confirmed, against Asana itself, that the data we're about to grade is
complete and correct?"* — a check the system performs on its own schedule,
regardless of how quiet the board is. In short: **it will stop confusing
"nobody edited anything" with "the data is broken."** A quiet weekend will pass
cleanly; a genuinely stuck data feed will still be caught within hours. Both
facts — when the data was last confirmed, and when a person last edited —
will be shown side by side, never blended into one number. And it won't be
declared done on our say-so: it has to prove itself over a 14-day observation
window (passing at least 95% of healthy runs and catching real problems within
8 hours) before the pause officially ends.

Three follow-up improvements riding alongside it:

1. **A watchdog for silence** — an alert that notices when a scheduled job *doesn't run at all* (a silently stopped job produces no error, so today nothing pages; this has bitten us twice, including the checker itself skipping runs unnoticed).
2. **Equal forensics for failed runs** — when a run stops, it will record the same timing detail a successful run records, so failures can be diagnosed as precisely as successes.
3. **Capacity early-warning** — a visible trend on the offer counts against the 1,000-row reading limit (currently ~67 and ~48, about 15x headroom), with an alarm well before the line is ever approached, so growth can't silently hit a ceiling.

---

## 6. Questions this report can answer next time

This brief comes from the same measurement machinery that runs the checker —
which means it can produce recurring, team-facing numbers on request. Candidate
regulars for brief #2; tell us which of these (or what else) you'd actually
use:

1. **Per-section quiet-time leaderboard** — which sections have gone longest without an edit, week by week. (Useful for spotting forgotten corners of the board.)
2. **Launch-pipeline dwell time** — how long offers sit in the ACTIVATING sections before reaching ACTIVE, and whether that's trending up or down.
3. **Budget expected-vs-actual roll-up** — `weekly_ad_spend` on the tasks vs what campaigns actually spent, totalled and per account, so budget drift is visible as one number instead of scattered flags.
4. **Ghost / missing-campaign trendline** — a weekly count of each, so the team can see whether board-vs-campaign alignment is improving.
5. **Monday-morning weekend digest** — what moved (and what didn't) over the weekend, waiting in the channel when the week starts.

Send asks to the operator; anything measurable from the account-health run or
the board's edit history is fair game.

---

## Appendix — artifact pointers (operator-only)

*Not for team distribution; every claim above traces to one of these.*

| Claim in this brief | Source artifact |
|---|---|
| 29-day / 175-run edit-cadence measurement; 92 vs 26 advances; median 1.1 h vs 21.0 h; 0 weekend edits ×4 weekends; 93.1 h clean max dormancy; Monday-morning spread max 88.3 h (3.68 d); 0/175 pass replay; ~39 min total passing window; "no threshold works" | `.sos/wip/EVIDENCE-w1-cohort-spread-14day-2026-08-12.md` (§0, §2.1–2.3, §3, §4.4, §5, §6) |
| Old gate measured an internal technical timestamp (cache-entry age), not data age; the 3600 s vs 16200 s contract collision; skipped-runs-silent finding | `.sos/wip/DIAG-S1-cadence-2026-08-11.md` (F1.1–F1.4; Q1 verdict) |
| Capacity headroom 67/1000 and 48–49/1000 ≈ 15x; FU-1/FU-2/FU-3 definitions | `.ledge/decisions/CARDS-follow-up-initiatives-2026-08-11.md` |
| Content axis live since Aug 11 ~20:00 UTC; last full pass at Aug 11 16:0x UTC tick (old clock); aborts honest, data served complete (68/68, 48/48 on every tick); serving path healthy; every reading errs stale never fresh | `.ledge/reviews/ATTEST-rel6-realize-offers-content-axis-2026-08-12.md` (§3, §4, §5.6, §7.1–7.4, §7.7) |
| Pause is deliberate and ruled — "Accept until replaced", honest aborts, no clock, successor's landing is the only exit (P-3); both-numbers-disclosed-separately (P-1); naming fence (P-12) | `.ledge/decisions/RULING-operator-option4-interview-2026-08-12.md` |
| Rebuilt checker = verification-recency gate; staged K-lane (dark stages, single behaviour-changing switch, never bundled); Stage-2 bar ≥95% healthy-pass / ≤8 h detection over a 14-day soak | `.ledge/decisions/ADR-007-verification-axis-gate-2026-08-12.md` (§7.0–7.6) + `.ledge/decisions/PACKET-option4-interview-stack-2026-08-12.md` |
| Verdict definitions (ghost/missing/transitional/aligned; budget 5%/20%; billing rules; three-way 10%; hollow/barren; advisory vs indeterminate vs healthy; enrollment-cohort roll-up; office_phone+vertical keying; #account-health channel; severity render order; block-cap truncation honesty) | autom8y monorepo @ origin/main: `services/account-status-recon/src/account_status_recon/rules.py`, `models.py`, `report.py`, `joiner.py`, `config.py` |
| 4-hourly run cadence | tick series in the ATTEST/EVIDENCE artifacts (00/04/08/12/16/20 UTC organic ticks) |

**Caveats carried honestly:** the 29-day window contains no public holiday
(holiday quiet would be longer than anything measured); the first ~14 days of
the window include a possible re-seed artefact, so all headline figures were
cross-checked against the clean 15-day segment and agree in direction and
magnitude; the "15x headroom" counts move slightly day to day (67–68 active,
48–49 activating in the receipts).
