---
type: review
status: accepted
artifact_id: GATE-pt02-fork-surface-2026-08-12
initiative: asana-native-insight-delivery
gate: PT-02 (hard — is the GATE-FORK decision surface honest and two-sided?)
seat: pythia, revision 2 (post PT-01 + probes)
date: 2026-08-12
verdict: FORK SURFACE HONEST WITH CONDITIONS
inscribed_by: main thread (the seat has no Write tool; this is its report of record)
---

# PT-02 — FORK SURFACE GATE

**Verdict: `HONEST WITH CONDITIONS` — upheld, at the boundary.**

Every artifact is individually scrupulous, but **no artifact owns the fork**; the
one place its terms sit side by side is **stale in both directions**, and the
night's four seats produced **32 Mission-A lines to 1 Mission-B line**.

> **The boundary, stated so it can be enforced**: if the briefing **annotates**
> item 2's `SAY-ABLE` rather than **withdrawing** it, this verdict becomes
> `FORK SURFACE COMPROMISED`. Annotation would preserve a verdict whose stated
> gate is refuted — the one move that converts a coverage gap into a
> misrepresentation.

**Why not COMPROMISED**: *"A surface is compromised when its error-finding
machinery has stopped working. This one is working unusually well."* S4 graded
its own option-space MODERATE and was vindicated twice; S1 recorded its own
directional bias as calibration data, and that record is what let PT-01 predict
the next error. What failed is **coverage**, and coverage gaps are what
conditions are for — provided they are named.

## The narrowing — measured

| artifact | "Mission A" | "Mission B" |
|---|---|---|
| S1 · S3 · S4 | 3 · 1 · 20 | 0 · 0 · 0 |
| three critiques | 3 · 0 · 3 | 0 · 0 · 1 |
| two FINDINGs + census | 2 · 0 · 0 | 0 · 0 · 0 |
| **total** | **32** | **1** |

**Mission A gained five cost reductions.** **Mission B gained nothing and
acquired a new blocker** (K-0c).

**The cause is the sprint roster, not any seat's judgment.** `IGNITION…:139`
reads verbatim: *"NOT IN THIS SPRINT: **S5**"* — B's only spine sprint, fenced out
for a correct `window_bound` reason. **A became the default by accumulation of
detail. No seat argued for A.**

**The stale fork table cuts the other way.** `shape.md:436-448` still shows A's
source-of-record as *"UNDECIDED… leading candidate is uncontracted"* — discharged
tonight. So it **understates A** while B's rows stay current. *Neither the fresh
artifacts nor the stale table is a fair surface.*

## The correction that most changes the decision

**Mission B's substrate is frozen-and-complete, not starved.** Verified live,
read-only:

```
bucket : autom8y-asr-verdicts          objects: 101
oldest : …/verdicts/dt=2026-07-18/…    2026-07-18T09:38:02Z
newest : …/verdicts/latest.json        2026-08-11T16:01:06Z
frozen : 29h 27m as of 2026-08-12T21:28:02Z
```

The corpus says *"starved until K-4"* in **five** load-bearing places. **Two
different things are being conflated.** The *Slack render path* is abort-starved
— true. The *record* is **frozen at a complete state**. "Starved" says *there is
nothing to deliver, wait indefinitely*; "frozen and complete, and its payload is
what P-3 withholds" says *the data exists, and the operator's own standing ruling
is what refuses it* — **which is rulable now**.

**B's real blockers**: CR-2 (§5(b) access, available now) · the P-3 payload
question · NF-1 (404 confirmed live) · unproven demand (shared with A).
**Neither of the first two requires K-4.**

## The "both" branch has never been priced

It appears in the fork's *statement* and nowhere in its *analysis*. Given the two
branches share no code, no repo, no rite and no gate, **"both" is plausibly the
cheapest option relative to its value — and nobody has checked.** An
option-enumeration failure at the fork itself.

## Gate-(b) neutrality — SURVIVED, under adversarial pressure

The arch critic graded S3 rev-1 **MILD TILT** and named a material omission —
`orchestrator.py:1224-1227`'s *"customer-facing channel"*, adverse to reading (a).
S3 rev-2 repaired both. **The ambiguous datum is filed in BOTH columns with the
ambiguity stated in both** — *"Recorded, not adjudicated."* The editorialising
imperative was withdrawn and replaced with a paired reciprocal cost, closing:
*"Neither is an argument. Both are consequences."* The asymmetry named in kind:
**reading (a)'s failure mode is silent; reading (b)'s is friction.**

**The census cuts both ways and the corpus carries the adverse edge at equal
weight**: *"a surface actively broadcasting is a **stronger** candidate for
gate-(b) scrutiny than a dormant one."*

## What the operator is not being told — ranked

1. **The option slate is not closed, and its floor has been falsified.** Option
   (g) was missed by the sprint that enumerated the slate; tier (iii) is now
   *"uncontracted and unverified."* *A missed option is an omission you might
   have found anyway; **a falsified impossibility claim is one you'd rely on to
   stop looking.*** *(This refines the main thread's "extended twice": option (h)
   is **not** verifiably new — the `dataframe_cache_put` series falls in S4's
   rejected (a)/(e) class, and retained frame objects **are** S4's disqualified
   option (f). One verified missed option plus one falsified impossibility claim
   is a sharper indictment than two missed options.)*
2. **Mission B is frozen-and-complete, not starved.**
3. **"Three say-able readouts" over-claims.**
4. **Mission B's deliverable was never run through S1's own predicate.** Items
   3/4 are refused for being *two-clock derived*; B's deliverable is
   **single-source and self-timestamped** — the property that made 1a say-able.
   The inference *"verdict-class is refused, therefore B is refused"* is
   available from the corpus and **is not correct**.
5. **The seat-error direction is a calibrated, predictive signal** — four
   movements, all toward say-able, the fourth wrong, and PT-01 predicted it.
   The operator is shown outcomes, not the signal.
6. **The K-lane is not unblocked.** K-1 gates on K-0a **and** K-0b **and** K-0c.
   Net movement toward K-4: **none**.
7. **The "both" branch has never been priced**; two composition questions unowned.
8. **The falsified `68/68` premise is still live** in the frame, `REPORT…:205`
   and `DESIGN-option4…:1188`.
9. **`honest_contract_complete` carries the same defect class** —
   `is_honest_complete()` returns True **vacuously for an empty manifest**
   (`section_persistence.py:268-269`) and is blind to never-attempted sections.
   Unflagged by S1 and its critic.
10. **UV-P-2 hard-blocks GATE-FORK and is open.**

## Conditions

| # | condition |
|---|---|
| **C-1** | Restate Mission B's gate correctly — frozen-and-complete, blockers = CR-2 + the P-3 payload question, render path distinguished from record |
| **C-2** | Refresh the §4.1 fork table |
| **C-3** | Disclose the sprint-roster asymmetry — **B's terms are unchanged for a scheduling reason, not an evidential one** |
| **C-4** | Carry S3 §7 in full, both columns; cite the `.ledge/reviews/` census path; correct `slack_post` → `slack_post_attempt` |
| **C-5** | *Superseded by PT-01's C-2* — one corroborated + two seat-attested, one carrying a refuted gate. **Never "three say-able readouts."** |
| **C-6** | **HARD — WITHDRAW item 2's `SAY-ABLE`; do not annotate.** Annotation flips this gate to COMPROMISED |
| **C-7** | **HARD — WITHDRAW tier (iii).** Restate as "uncontracted and unverified" |
| **C-8** | **State that the slate is OPEN**, name the unswept candidates with the §B caveat, assign the two unowned composition questions |

## The seat's own three corrections

1. **Correction (a) CONFIRMED at STRONG** — independently corroborated by
   sampling tick 7 live; method audited and attacked. **No separate ASR outage.**
2. **Correction (b) CONFIRMED, and worse than stated** — the `68/68` completeness
   claim was its own, and it is withdrawn. *"I asserted a property of a receipt
   from its shape without reading its derivation."*
3. **"K-0a was the highest-leverage unblocked item" — leverage OVERSTATED, same
   error class.** K-1 gates on **three** preconditions and a second was found
   blocked the same night. **K-0a's PASS is real and well-executed; the lane did
   not move.** *Reasoning from a component's shape to a system's state.*

**GATE-FORK remains unruled.** Nothing here picks A, B, or both. The gate-(b)
scope question, O-7, K-0b, OS-1/OS-2, telos ratification and CR-2 access are
untouched. Free until **2026-08-18**.

**Live-world scope**: three AWS read calls, read-only git plumbing, file reads and
greps. **Zero writes of any class.** One disclosure: it read
`autom8y-asr-verdicts` (list + head, **no GET**) and **discloses rather than
assumes** that this is inside the CR-2 fence — the eunomia seat took the stricter
reading and did not touch it. If that stricter reading governs, the probe was out
of bounds and the operator should say so.
