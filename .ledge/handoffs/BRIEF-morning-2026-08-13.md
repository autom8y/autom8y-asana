---
type: handoff
status: accepted
artifact_id: BRIEF-morning-2026-08-13
initiative: asana-native-insight-delivery + offers-freshness-axis-contract
date: 2026-08-12
for: OPERATOR
authority: overnight campaign under the operator's standing sign-off, full authority through the landing seam, no client or team communication
---

# MORNING BRIEF — 2026-08-13

**Nothing needs your attention before coffee. Nothing is broken. Nothing was
communicated to anyone. No rail was exercised, no Asana object touched, no
production behaviour changed.**

One thing landed in production last night and it was already yours: PR
autom8y#1555, the ASR `image_tag` pin. Everything else is paper — read-only
evidence and adversarially-reviewed decision artifacts.

---

## 1. READ THIS FIRST — the two things that changed your decisions

### (a) GATE-FORK is a different choice than it was at sunset

Three separate corrections moved it, none of them from the seat that made the
original claim:

- **Mission A's retrospective half is REACHABLE.** S4 had returned a "negative
  result" saying it was not. Its critic found an option **nobody had
  enumerated** — `GET /api/v1/offers/section-timelines`, mounted
  unconditionally, in the published OpenAPI, replaying Asana section history over
  an arbitrary window. S4's §11 *"if and only if"* is **withdrawn as false**. It
  would have told you to rule that the readout must begin its history at first
  run. You were about to be asked to give up something you already have.
- **Mission B is NOT starved.** The corpus says "starved until K-4" in **five**
  load-bearing places. PT-02 verified live: **101 complete verdict records,
  2026-07-18 → 2026-08-11T16:01:06Z, frozen 29.4 hours.** The *Slack render path*
  is abort-starved; the *record* is frozen-and-complete. B's real blockers are
  **CR-2 (§5(b) access) and the P-3 payload question — both rulable this week,
  neither requiring K-4.** As written, B looks indefinitely blocked. It is not.
- **The option slate is OPEN, and its FLOOR has been falsified.** This is the
  night's largest single omission, and PT-02 corrected my first framing of it —
  I had said "extended twice"; it is sharper and worse than that. The slate was
  **extended once** (option (g), missed by the very sprint that enumerated the
  slate, with the file open). And separately, S1's tier (iii) — *"edit history is
  **genuinely absent and not constructible**"*, its **only** remaining
  "expensive" cost tier — is **falsified**. PT-02's words: *a missed option is an
  omission you might have found anyway; a falsified impossibility claim is one
  you would have relied on **to stop looking**.*

  I traced the last link myself: `clients/stories.py:482-500` fetches
  `/tasks/{gid}/stories` with **no `resource_subtype` filter at all**, and the
  cache write does not narrow. Of nine admitted story subtypes, **six are
  edit-class**. The substrate does not exclude edit history — **one consumer
  discards it at read time.** One link stays open: whether anything fetches
  stories for *offer* tasks at all. That single probe also settles option (g)'s
  cache warmth.

### (b) The fork surface had quietly narrowed — measurably, and nobody's fault

PT-02 counted mentions across the night's nine artifacts: **32 Mission-A lines
to 1 Mission-B line.** Mission A gained five cost reductions; **Mission B gained
nothing and acquired a new blocker.**

**The cause is the sprint roster, not any seat's judgment.** S5 is B's only
spine sprint and it was fenced out of the wave for a correct reason
(`window_bound`, must not deploy before 2026-08-18). Three sprints worked A's
side all night; zero worked B's. No one argued for A. **A became the default by
accumulation of detail.**

The one place the fork's terms sit side by side (`shape.md:436-448`) is now
**stale in both directions** — it still shows A's source-of-record as
"UNDECIDED", which is discharged. So it *understates* A while B's rows stay
current. Neither the fresh artifacts nor the stale table is a fair surface.

---

## 2. YOUR DECISION SET — 20+ routed items consolidated to seven

PT-01 deduplicated everything the four sprints routed to you. Ranked by leverage.
**All seven are free and unclocked** except where noted.

| # | decision | blocks | cost |
|---|---|---|---|
| **D-1** | **What do you know about the audience?** Was brief #1 delivered; has anyone asked for anything; what non-engineering surface does the team already use | **The honesty of GATE-FORK itself** — a null answer is *mission-reshaping*, not an obstacle. Also hard-blocks scoring an entire rail class | **Minutes. One message.** Highest leverage in the set — every other decision is cheaper to make well after it |
| **D-2** | **GATE-FORK** — A / B / both / neither-yet | every build sprint | one ruling; **free until 2026-08-18**. Honestly downstream of D-1 |
| **D-3** | **O-7** — does the zero-K-lane fence bar read-only *consumption* of a fenced field, as distinct from a *touch*? | S1's item-1a build path **and** S4's central K-lane attestation — the two contradict each other today | one ruling, no probe. Larger than S1 sized it |
| **D-4** | **The gate-(b) scope question** — modal scoped to Asana writes, or applied uniformly; and if uniform, prospective or categorical | whether telos rung 2 is reachable; your only live rail's autonomy | one ruling. Reading (a) fails **silently**; reading (b) fails as **friction** |
| **D-5** | **Which retrospective route**, and on what terms | the Mission-A limb only | one ruling, **after one cheap probe** (below) |
| **D-6** | Is a `k of n` denominator a "third number"? | DR-5, which binds **every published number in every readout** | one ruling |
| **D-7** | **K-0c — where does the contract of record live?** | K-0c → K-1 → **the entire K-lane** | one ruling; evidence supports promoting it to `.ledge/decisions/` |

**Six routings** (accept or decline, no analysis owed): security rite for the
S2S authorization gap · SRE for the cross-repo log-retention coupling · a card
for the 100-campaign cap · name a human owner for the offers schema/routes · a
**content** owner (not an engineer) for the enrollment explainer · **and the
`TemporalFilter` defect** (§4 below) — product correctness, found by an
initiative fenced from fixing it.

**One probe worth authorising before D-5**: *is the story cache warm for the
offers project independent of `section-timelines`?* It is cheaper than any build
and it settles **three** things at once — Mission A's real cost, whether option
(g) is usable, and whether the `TemporalFilter` defect is **active or latent**.
It needs your word because answering it may mean a live call.

**The cheapest probe on the board**, and it should precede D-5: *is the story
cache warm for the offers project independent of `section-timelines`?* It is
cheaper than any build and it moves Mission A's real cost. It needs your word
because answering it may mean a live call.

---

## 3. WHAT LANDED

**PR autom8y#1555 — MERGED `7bbb418e`.** The ASR `image_tag` pin now reads
`c21cab9`, equal to the resident image. The production rollback landmine is
disarmed; a `workflow_dispatch` apply is no longer a 19-day rollback past the
cure. Deployed image verified still `c21cab9`, `Active`, untouched.

**Stage-1 observability correction struck.** The "separate ASR outage, routing
owed to the operator" line is **withdrawn as over-called**. A 7-of-7 tick census
proves the ~24h darkness **is** the ruled P-3 posture, dated to the first tick
after the cure landed. **No triage is owed to you.**

**K-0a / B3-a PASSES.** 27/27 classified names resolve, 27/27 carry non-null
`last_verified_at`, oldest stamp **20.5 minutes**, **45 manifest versions swept**,
19 of 27 zero-row (matching ADR-007's "~19", proving the P-5 population was
measured and not the superseded one). **R-O8's held trigger has fired — you can
rule it.**

⚠ **But the K-lane did NOT move.** K-1 gates on **three** preconditions. K-0a
passed; **K-0b** is yours and undischarged; **K-0c is now BLOCKED** — the frozen
contract ADR-007 amends lives in gitignored `.sos/wip/`, so it cannot follow its
own precedent, which operated on a tracked `.ledge/decisions/` file. *(pythia
flagged this against itself: it had called K-0a "the highest-leverage unblocked
item" and, on the evidence, overstated the leverage the same way.)*

---

## 4. THE SPINE — four sprints, five adversarial passes, two gates

**PT-01: `SPINE COHERENT WITH CONDITIONS` · PT-02: `FORK SURFACE HONEST WITH CONDITIONS`.**
Ten conditions between them, every one an assembly or ruling act — **none
requires a sprint re-run.**

- **S1** — the say-able predicate. BLOCK → discharged after item 1a was attacked
  five ways and held all five.

  ### ⚠ The honest count is ONE, not three

  I wrote "three say-able readouts" earlier in the night. **Two of the three were
  withdrawn under adversarial pressure.** The final state:

  | item | verdict | why |
  |---|---|---|
  | **1a** — per-section quiet time | **`SAY-ABLE`** | rite-disjoint corroborated; attacked five ways, held five. **Real, and buildable now.** |
  | **2** — launch dwell | **WITHDRAWN** | G4 FAIL — the imputation error is **population-dependent in sign** (understates for offers currently ACTIVE, overstates for currently ACTIVATING). G4 exists to require a *known* direction |
  | **5a** — weekend moved-set | **WITHDRAWN** | G4 FAIL — see the defect below. Its "omission only" argument is false at source |

  **One readout is a better night's work than three claimed.** Each withdrawal
  came from a second reader going *one hop further* than the seat that made the
  claim — and each hop was short. That is the pattern, and it is the finding.

  ### A live product defect fell out of the last withdrawal

  Filed as `DEFECT-temporal-filter-imputed-false-move-2026-08-12.md`. **This is
  shipped-code correctness, not a say-ability question, and it is yours to route
  — the initiative that found it is fenced from fixing it.**

  `TemporalFilter.matches` treats `moved_to` and `since`/`until` as satisfiable
  by an interval's **own** fields; `moved_from` is the only criterion that
  consults a predecessor, and **its guard is opt-in**. An imputed interval
  carries `entered_at = task_created_at` and the offer's current classification.
  So a natural weekend query — *"what moved into ACTIVE between Saturday and
  Sunday"* — never reaches the guard, and **an offer merely created that weekend,
  which never moved, is returned as having moved.** Concentrated exactly where
  the query aims: the offers most likely to be imputed are the newly created
  ones. Reachable from a shipped CLI consumer today.

  The workaround **inverts** the sign rather than fixing it: specifying
  `moved_from` engages the guard, but no pre-first interval is synthesised, so it
  **drops every offer's genuine first move.**

  **Not measured**: whether any offer is imputed in production today. That
  depends on story-cache warmth for offer tasks — the same standing probe that
  gates option (g). If nothing is imputed, the defect is latent. **Nobody has
  checked.**
- **S2** — residue triage. Four residues **CLOSED with receipts**; the
  100-campaign cap has **six** operator surfaces, all *coincident*, no leading
  indicator. The only seat that committed no false-negative error all night.
- **S3** — delivery rails. Sixteen rails, each with a receipt or an explicit
  gap. **All three Asana write classes are BUILT**, not two.
- **S4** — Mission-A source of record. Recommendation survived; the negative
  result did not.

**Security finding worth your eye** *(recorded, not opened — the register is
yours)*: `require_service_claims` **authenticates but does not authorize**. It
returns `permissions=[...]`, but `entity_write.py` touches `claims` only for
logging, while `admin.py:456` genuinely checks `SUPER_ADMIN_PERMISSION`. **A
cache-refresh is permission-gated; an Asana board write is not.** JWT-mode lends
the bot PAT. The effective gate is **fleet membership, not authorization**, over
26 write endpoints. Nothing was exercised, and whether an agent seat could obtain
such a JWT was **deliberately not probed** — it needs live credentials.
**Consequence: CR-1 is a process fence standing where no technical one does. It
is not redundant.**

---

## 5. THE MOST USEFUL THING WE LEARNED

PT-01 was asked whether two seats making the same class of error was coincidence.
It found **three of four**, diagnosed the mechanism as structural, and
**predicted where the next one would be**. I ran the probe. **It was right, at
the first place it looked.**

The mechanism, in its words:

1. **The charge makes absence the honourable answer.** Under a floor reading
   *never confidently wrong*, every seat correctly inferred that over-claiming is
   the sin — then discharged that discipline by **over-refusing**, which the same
   floor does not punish.
2. **The receipt grammar cannot express a negative.** A presence is anchorable to
   `file:line`; an absence is not. So *a true scoped probe* and *a false general
   claim* are **indistinguishable at review time**. Every error tonight was a
   true receipt supporting a false claim.
3. **No gate anywhere fires on over-refusal.** Every one of these was caught by
   external critique or by a coordinator handing a seat a surface — **never by
   the seat's own machinery.**

I committed the identical error myself and PT-02 caught it: I quoted an event
name as `slack_post` that my own command had **truncated mid-token** at
`…"event": "slack_pos`. The real events are `slack_post_entered` →
`slack_post_attempt` → `report_posted`. Corrected in place, with the mechanism
recorded.

### The final tally, and what it recommends

Across five revisions and three delta passes: **three findings against the
author, three concessions by the critic, and one gate the critic convicted
itself of.** The gate in question — G4 — asked *"is the error direction
**known**?"*, which is **answerable by assertion** and never forced anyone to
enumerate branches. That is how both withdrawn readouts passed it.

> **No gate, no self-flag and no calibration note ever caught this class. A
> second reader going one hop further caught it five for five.**

And every missed read was **adjacent** — one `frozenset`, one call-hop, one
module. The sharpest instance is in the artifact's own evidence: revision 4's
**self**-re-test of item 5a returned a **false PASS** because it was run at the
wrong layer, while a correctly-aimed doubt sat beside it in the same table and
did not outweigh it. *That is the argument for a second reader over a
self-check, made by the seat that ran the self-check.*

A replacement gate (**G4′** — enumerate every imputation, default, filter and
clipping branch from source event to rendered figure; state the sign on each;
pass iff all non-neutral branches share one sign) decides all three items
mechanically. But the seat that adopted it stated its limit honestly: **it
compels enumeration, not completeness of enumeration** — *"an author who has not
read `temporal.py` enumerates what they know and stops."* **It is not what caught
anything.**

**So the recommendation is a staffing one, not a process one.** The spine's
discipline is excellent at catching over-claims and structurally blind to
over-refusals, and the only reliable detector is a second reader with a mandate
to go one hop past where the argument stops. That is cheap. It was the whole
difference tonight.

---

## 6. STILL OPEN, DELIBERATELY

**Untouched because they are yours**: GATE-FORK · the gate-(b) §OPEN scope
question (undecided in **both** directions) · OS-1/OS-2 · telos ratification ·
CR-2 access · O-7 · K-0b · opening any card in the register.

**S5 excluded** — `window_bound: true`, must not deploy before **2026-08-18**.

**Two artifacts carry falsified premises still uncorrected elsewhere.** The
68/68-as-completeness claim was corrected in the telos (both places) and in S1.
It is **still live** in `frames/…:73,:166,:391`, `REPORT-asr-team-brief…:205`,
and `DESIGN-option4-…:1188`. Its **gate/attestation** uses are correct and must
**not** be changed — there the pair is used as a non-truncation receipt, which is
exactly what it is.

**One unresolved echo**: `honest_contract_complete` — the receipt S1 chose
`/rows` to obtain — **may carry the same defect**. `is_honest_complete()` returns
True iff no section is FAILED, and **True vacuously for an empty manifest**. A
section never *attempted* is not FAILED; it is absent, and invisible. Neither S1
nor its critic flagged it. **Routed, not ruled.**

**Housekeeping, yours to call**: 51 worktrees in this repo, most long-finished ·
the deadman-fill worktree from yesterday still on disk · the monorepo checkout is
on a divergent branch with a **sibling session actively committing** — every seat
read `origin/main` via `git show`, which is why nothing was corrupted.

---

## 7. HOW TO SPEND THE FIRST TEN MINUTES

1. **D-1.** One message. It can reshape an initiative and it is free.
2. **D-7.** One ruling. It unblocks the entire K-lane and the evidence points one
   way.
3. **D-3.** One ruling. Two artifacts currently contradict each other on it.

Everything else can wait for the 18th.
