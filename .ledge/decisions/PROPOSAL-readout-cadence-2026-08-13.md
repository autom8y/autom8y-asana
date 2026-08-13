---
type: decision
status: proposed
status_note: "PROPOSAL — input to operator Q-2, NOT a ruling. Cadence is UNRULED (C-9)."
artifact_id: PROPOSAL-readout-cadence-2026-08-13
initiative: exec-insight-delivery (asana-native-insight-delivery)
sprint: EX-5 (WS-2 — DESIGN limb; EXIT HELD pending Q-2)
rite: 10x-dev
author_seat: requirements-analyst
disjoint_critic: eunomia / verification-auditor (NR-5, §A mandate)
date: 2026-08-13
impact: low
impact_categories: []
evidence_grade: MODERATE (self-attestation cap; this is a recommendation, not a ruling)
decision_owner: OPERATOR (C-9 — cadence is UNRULED; see RULING-operator-morning-set-2026-08-13.md §2 item 9)
binding_inheritance:
  - RULING-operator-morning-set-2026-08-13.md:70-82 (R-5 — two artifacts; the recurring readout exists and recurs)
  - RULING-operator-morning-set-2026-08-13.md:203-204 (§2 item 9 — cadence/template/content UNRULED)
  - .know/telos/asana-native-insight-delivery.md:145-149 (RUNG 2 — "on its own cadence, TWO consecutive occurrences, WITHOUT a human assembling it")
  - .know/telos/asana-native-insight-delivery.md:154-162 (RUNG 4 / the felt bar — exec rung RUNG E is its parallel, R-15)
  - .sos/wip/frames/exec-insight-delivery.shape.md:381-388 (EX-5 exit criterion 2 — DF-2)
supersedes: none
---

# PROPOSAL — the recurring readout's cadence

> **This is a PROPOSAL, not a ruling.** Cadence is the design surface's spine and
> it is **not a seat's to assume** (C-9). `RULING-operator-morning-set-2026-08-13.md`
> §2 item 9 records the recurring readout's cadence, template and content as
> **UNRULED**. This document enumerates the cadence options with their tradeoffs
> and **recommends** one, as **input to the operator's Q-2**. Nothing here is
> recorded as decided. The recommendation is marked as a recommendation
> throughout and never as a default.

## §0 What is being scheduled

The recurring readout carries exactly **one say-able number** — **item 1a**:

> *"At the {t} observation, these sections' most recent observed offer edit was
> {t_s}"* — read via `POST /v1/query/offer/rows`, subject to **DR-2** (the
> reported as-of is the `min` floor over constituents).
> (`PREDICATE-sayable-set-under-refusing-verdict-axis-2026-08-12.md:43-48`.)

Cadence is *how often that readout is generated and delivered*. It is the single
highest-leverage operator input in the whole EX-5 DAG
(`shape.md:366-370`): if Q-2 lands in the Phase-0 operator pass, EX-5 joins Phase
1; if not, EX-5 holds to Phase 2. This proposal exists so the operator can rule
Q-2 with the tradeoffs in front of them.

## §1 The option slate

Enumerated per `option-enumeration-discipline` §5 (three structurally distinct
fixed cadences + one null + one externally-prompted mechanism + one
bounded-adaptive hybrid — option **G**, added at the §A external critique per
option-enumeration-discipline §6, enumerated-and-rejected). The options are
**structurally distinct** — they differ in the *scheduling mechanism* (fixed
calendar interval vs. event-trigger vs. pull vs. floor+escalation), not merely in
a parameter.

| # | Option | Scheduling mechanism | RUNG E clearance (2 consecutive) | UV-P-E-1 derivable? |
|---|--------|----------------------|----------------------------------|---------------------|
| **A** | **Daily** (each business morning) | fixed calendar interval, 1 day | ~2 business days from first occurrence | **YES** — deadline = first + 1d + margins |
| **B** | **Weekly** (fixed weekday AM) — **RECOMMENDED** | fixed calendar interval, 7 days | ~2 weeks from first occurrence | **YES** — deadline = first + 7d + margins |
| **C** | **Fortnightly** (every second week) | fixed calendar interval, 14 days | ~4 weeks from first occurrence | **YES** — deadline = first + 14d + margins |
| **D** | **Monthly** | fixed calendar interval, ~30 days | ~8–9 weeks from first occurrence | **YES** but LATE — see §2 |
| **E** | **Event-triggered** (emit when the `min`-floor as-of crosses a staleness bound) | freshness-threshold trigger; no fixed interval | indeterminate — occurrences are not scheduled | **NO** — breaks DF-2 (see §3) |
| **F** | **On-demand / no fixed cadence** (exec or operator pulls it) — *the null option* | human pull; no cadence | never — a pull is not an "own cadence" occurrence | **NO** — breaks DF-2 and RUNG 2 (see §3) |
| **G** | **Bounded-adaptive hybrid** (weekly floor + event-escalation when the `min`-floor as-of crosses a staleness bound) | fixed weekly floor + conditional event-trigger | ~2 weeks on the floor occurrences | **PARTIAL** — the weekly floor is derivable; the escalation occurrences are not scheduled (see §3.G) |

### Per-option tradeoffs

**A — Daily.**
- *For*: fastest RUNG E clearance (two consecutive occurrences in ~2 business
  days); most responsive to a pipeline stall (item 1a's only non-neutral error
  branch is frame-staleness → the age reads older, §G4′ below, so a stall is
  exactly what item 1a surfaces).
- *Against*: item 1a is a **recency** figure whose honest day-over-day delta is
  usually noise — `max(last_modified)` on a healthy pipeline moves a little every
  day and says nothing new. Daily delivery of a slow-moving figure is the
  **nag/tune-out** failure mode, and the reader is a CEO and cofounder
  (`RULING…:32-34`). It presses against R-16's orientation register: a readout
  that arrives every morning is read as an alert stream, which invites the reader
  to treat its arrival as a call to action — the exact steering the rung forbids.

**B — Weekly (RECOMMENDED).**
- *For*: matches the **signal grain** of a recency metric — week-over-week change
  in "most recent observed edit" is meaningful where day-over-day is noise. Fits
  an existing weekly-digest cadence intuition (the "Monday-morning weekend
  digest" framing — note item 5a *itself* was **WITHDRAWN** as a say-able number
  at `PREDICATE…:1182`, on say-ability grounds, not cadence grounds, so the
  *timing* intuition stands independent of the withdrawn number). A weekly briefing reads as
  orientation, not as an alert — aligned with R-16 / F-E3. Keeps RUNG E **near
  term and derivable** (two occurrences in ~2 weeks; see §2).
- *Against*: a pipeline stall that begins the day after a delivery is not
  surfaced to the exec for up to a week. **This is acceptable and by design**:
  freshness *alerting* is the job of the PROV-family alarm on the warmer side
  (`CONTRACT…:742-753`, AL-5-HOME), **not** of an exec orientation readout. The
  readout reports state; the alarm pages. Conflating the two is the AL-5 error
  the contract exists to end.

**C — Fortnightly.**
- *For*: lowest delivery volume of the fixed cadences; strongest anti-nag.
- *Against*: RUNG E clearance slips to ~4 weeks; and a two-week-old recency figure
  is coarse enough that the exec cannot distinguish "the pipeline is healthy" from
  "the pipeline stalled ten days ago" without cross-checking the alarm anyway.

**D — Monthly.**
- *For*: minimal footprint.
- *Against*: two consecutive occurrences take ~8–9 weeks, pushing RUNG E
  verification **past** the telos's Mission-A limb deadline of `2026-09-30`
  (`.know/telos/…:164`) and near/over the placeholder `2026-11-01`. A monthly
  recency figure is too coarse to orient on. Enumerated and not recommended.

**E — Event-triggered (freshness-threshold).**
- This is the option a skeptical external reader adds, and it is enumerated
  precisely **because it fails the derivability test** and thereby shows what
  makes UV-P-E-1 derivable. An emission fired when the `min`-floor as-of crosses a
  bound has **no predictable cadence** — occurrences are conditional on substrate
  state, so "its own cadence, TWO consecutive occurrences" (RUNG 2) has no
  schedule and UV-P-E-1 cannot be computed as a date. It also **re-imports the
  AL-5 confusion** the freshness contract just removed: an event-triggered
  *readout* is a staleness detector wearing a briefing's clothes.
- *Verdict*: **not a cadence.** It is an alarm, and that job is already owned by
  the PROV-family successor (`CONTRACT…:742-753`).

**F — On-demand / no fixed cadence (the null option).**
- The "why add a cadence at all" option. The exec or operator pulls the readout
  when they want it.
- *Against*: a pull has **no cadence**, so it cannot satisfy RUNG 2's "on its own
  cadence" and cannot produce "two consecutive occurrences" that a receipt can
  join; and a pull is one keystroke from the hand-assembly the founding artifact
  proves is the easy failure. UV-P-E-1 is **underivable** (no schedule → no
  deadline). Enumerated as the null so the burden of adding a cadence is
  explicit: **a scheduled cadence is the thing that makes RUNG E observable at
  all.**

**G — Bounded-adaptive hybrid (weekly floor + event-escalation).**
- The option that sits squarely on the **A↔B tension** a skeptical reader would
  raise: keep weekly's orientation register as the floor, but fire an *extra*
  occurrence when the `min`-floor as-of crosses a staleness bound — buying
  daily's responsiveness only when it matters, without daily's everyday nag.
- *Against (enumerated-and-rejected)*: the event-escalation limb is **option E
  wearing option B's clothes.** It re-imports the exact **AL-5 confusion** the
  freshness contract just removed — a readout that escalates on staleness *is* a
  staleness alarm — and freshness alerting is already owned by the warmer-side
  PROV-family alarm (`CONTRACT…:742-753`), the separation-of-concerns line §2
  reasoning 4 draws. It also **partially breaks DF-2**: the escalation
  occurrences have no schedule, so only the weekly floor's UV-P-E-1 is derivable
  — and because the rung clears on the floor occurrences regardless, the
  escalation adds alarm-behaviour without adding rung value. **Rejected** — but
  enumerated so the A↔B middle is refused *explicitly*, not left absent
  (`option-enumeration-discipline` §6). If the operator wants staleness
  responsiveness, the honest home for it is the PROV-family alarm, not the
  readout cadence.

## §2 The recommendation and its reasoning

**Recommendation (recommendation, NOT a ruling): Option B — weekly, delivered a
fixed weekday morning (Monday AM proposed).**

Reasoning, in priority order:
1. **Signal grain.** Item 1a is a recency figure; its meaningful unit of change is
   the week, not the day. Weekly delivers signal; daily delivers noise dressed as
   signal.
2. **Orientation register (R-16 / F-E3).** A weekly briefing is read as
   orientation. A daily arrival is read as an alert stream and invites the
   arrival itself to be treated as a call to action — the steering the rung
   forbids and that is silent in every success signal.
3. **RUNG E stays near-term and derivable.** Two consecutive weekly occurrences
   clear in ~2 weeks, well inside the telos horizon (§3).
4. **Separation of concerns.** Freshness *alerting* is the warmer-side
   PROV-family alarm's job (`CONTRACT…:742-753`). The readout orients; the alarm
   pages. Weekly keeps that line clean; event-triggered (E) erases it.

**Runner-up: Option A (daily).** It clears RUNG E fastest (~2 days) and is the
correct choice **if** the operator's priority is the earliest possible RUNG E
receipt over signal-to-noise and anti-nag. The tradeoff is stated with eyes open:
daily buys speed of verification at the cost of delivering a slow-moving figure
into a CEO/cofounder inbox every morning.

**No recommendation divergence is being suppressed.** The operator may weight
speed-to-RUNG-E (favours A) above signal-grain and anti-nag (favours B); this
seat cannot see that weighting and does not rule it. C-9 governs.

## §3 DF-2 — how this proposal makes UV-P-E-1 derivable

**The gap today.** RUNG E's deadline is `UV-P-E-1`, currently the **placeholder**
`2026-11-01`, explicitly labelled a placeholder to be re-derived the moment
cadence is ruled (`shape.md:386-387`, `:968-970`). A placeholder is not a
derived deadline; DF-2 is the requirement that this proposal make the deadline
**derivable**.

**The derivation.** RUNG E limb (a) requires the exec to receive/open the readout
**on its own cadence at least TWICE** (`.know/telos/…:154-158`; the "at least
TWICE" count is the frame's DV-4 derivation, `shape.md:39`). The deadline is a
function whose **only free variable is the cadence interval**:

```
UV-P-E-1  =  first_automated_occurrence_date
           +  (N - 1) x cadence_interval            # N = 2 : the "at least TWICE" count
           +  exec_receipt_margin                    # room for a real in-anger "opened it twice" observation
           +  attestation_margin                     # eunomia / verification-auditor limb-(a) receipt

where cadence_interval = { A: 1 business day | B: 7 days | C: 14 days
                          | D: ~30 days | E,F: UNDEFINED -> deadline underivable }
```

**Discharge.** Options A–D make the deadline **derivable** (the interval is a
constant); options E and F leave it **underivable** (no schedule). Ruling any of
A–D therefore discharges DF-2 mechanically — the placeholder `2026-11-01` is
replaced by the computed date.

**§3.G — the hybrid's partial derivability.** Option G's weekly *floor* makes
UV-P-E-1 derivable exactly as B does (floor interval = 7 days); its *escalation*
occurrences are conditional on substrate state and carry no schedule, so they
contribute no derivable date and no rung value beyond the floor (the rung clears
on the floor occurrences). G is therefore derivable-on-the-floor but rejected on
the separation-of-concerns ground (§1 G) — the escalation limb is a staleness
alarm, which the PROV-family alarm already owns.

**Worked under the recommendation (illustrative — the *formula* is the discharge,
not the date).** Under Option B (weekly), with the first automated occurrence
landing after the Phase-2 generation build (the earliest realistic first
occurrence is not before the Phase-2 build lands, so it is stated as a variable,
not asserted):

- `first_automated_occurrence_date` = D0 (Phase-2, unknown at this limb)
- `+ 1 x 7 days` (second occurrence)
- `+ ~2 weeks` exec_receipt_margin (a genuine "received/opened it twice" in-anger
  observation, not a same-day double-post)
- `+ ~1 week` attestation_margin

→ `UV-P-E-1 ≈ D0 + ~5 weeks`. If D0 falls in early September, the derived
deadline lands **near the telos's Mission-A limb `2026-09-30`** and **well inside**
the `2026-11-01` placeholder — i.e. the placeholder is loose, not tight, under the
recommended cadence. **The operator's Q-2 ruling fixes the interval; the date then
computes. That is DF-2 discharged.**

> **What this proposal does NOT do.** It does not set D0 (that is the Phase-2
> build's, and the first occurrence cannot be asserted before the mechanism
> exists), and it does not ratify RUNG E's text (Q-1, operator-owned,
> `shape.md:637`). It makes the deadline a **function of a single ruled
> variable**, and recommends the value. Until Q-2 lands, `UV-P-E-1` stays the
> labelled placeholder with its gap named — which is the honest state, per
> `shape.md:606` gate 7.3.

## §4 Fences honoured

- **C-9** — cadence is UNRULED and is recorded here as a PROPOSAL, never as
  decided. The recommendation is marked as a recommendation.
- **R-16 / F-E3** — the cadence reasoning is built around the orientation
  register; no option is recommended on a steering rationale.
- **No infra mutation, no authenticated call, no git.** This is a decision
  proposal authored as a file.

## §5 Impact assessment

`impact: low` · `impact_categories: []`. This artifact is a decision proposal; it
crosses no architectural boundary, changes no schema, API contract, or auth flow,
and touches no security-sensitive path. The delivery it schedules reads a
**shipped** response field via `POST /v1/query/offer/rows` (read-only; "reading is
not touching" per R-4, `RULING…:55-68`) and posts to Slack, a delivery chain that
already exists (`shape.md:1023`, NR-4: `slack_post_entered → report_posted`). The
cross-service character of the **generation build** is Phase-2's to (re)assess
when principal-engineer joins; nothing in this proposal builds it.
