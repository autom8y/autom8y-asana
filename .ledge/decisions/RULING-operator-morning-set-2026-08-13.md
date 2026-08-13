---
type: decision
status: accepted
artifact_id: RULING-operator-morning-set-2026-08-13
initiative: asana-native-insight-delivery + offers-freshness-axis-contract
date: 2026-08-13
ruled_by: OPERATOR (direct, in-session, /interview with AskUserQuestion)
anchor: .ledge/handoffs/BRIEF-morning-2026-08-13.md (main @ f8c8391f)
binding_note: "Nothing the operator did not explicitly rule on is recorded here as decided. See §NOT COVERED."
protocol: >-
  One decision per question · assumptions stated before asking · recommendations
  revealed only AFTER each answer and marked as recommendation, never as default ·
  "wrong question / none of these" available in every set · HOLD first-class with a
  named revisit trigger · read-backs where an answer reframed the question.
---

# OPERATOR RULING — the morning decision set

Fifteen rulings across four question sets. The consolidated set from PT-01 was
**D-1..D-7 + six routings + one probe**. It is now closed except where §NOT
COVERED says otherwise.

---

## §1 RULED

### R-1 · D-1 — the audience question: CLOSED, and it reframed the initiative
The operator did not answer the question as posed. They supplied a larger fact:

> **"we need a report that can be shared with my CEO and cofounder with max clarity"**

**Ruled**: the near-term audience is **the CEO and cofounder**. The initiative was
framed, shaped and telos'd end-to-end for *"the team working heavily through the
Asana frontend"*. That reader is now second.

⚠ **UV-P-2 is NOT closed by this.** *"Has the offers team asked for anything"*
remains **OPEN and unanswered** — the operator redirected to a different audience
rather than answering about this one. Any later seat inferring team demand from
this ruling is inferring something the operator did not say.

### R-2 · The story-cache probe — AUTHORIZED IN FULL
Live call to `GET /api/v1/offers/section-timelines` permitted, alongside AWS
reads. Settles three items at once: Mission A's real cost, whether option (g) is
usable, and whether `DEFECT-temporal-filter-imputed-false-move` is **ACTIVE or
LATENT**. Dispatched to a rite-disjoint eunomia seat with a **cold-cache caveat
requirement** — a first-ever invocation populating a cold cache is not a
measurement of steady state and must not be reported as one.

### R-3 · D-7 — the contract of record moves to `.ledge/decisions/`
**Ruled: promote.** Matches every sibling contract in this repo and the very
precedent K-0c cites (the charter amendment, which landed as a real PR against a
tracked file). **K-0c becomes a mechanical dispatch.** A pointer is to be left at
the old `.sos/wip/` path so existing citations do not dangle.

### R-4 · D-3 / O-7 — PERMISSIVE: reading is not touching
**Ruled: read-only consumption of a shipped response field is NOT a "touch"**
under the zero-K-lane fence.

Consequences, all of which follow mechanically:
- S1's item-1a build path **stands as written** (it may read `honest_contract_complete` and the truncation pair off `meta`).
- S4's K-lane attestation is **narrowed** — it claimed strength from the readout *not* reading `meta`; that is now a design choice, not a fence requirement.
- S1's **item 1b and §2.7 row 3** move from withheld-on-fence-grounds to **reachable**; they must be re-derived on their remaining grounds, not auto-promoted.

**Recommendation divergence, recorded**: the recommendation was the third option
(per-field, by the fence's own `:1504` test). **The operator ruled otherwise and
that governs.** The named tradeoff: the permissive reading makes the fence about
**mutation only**, so it no longer constrains read-coupling to K-lane-derived
values. That is a real widening, ruled with the consequence stated.

### R-5 · The exec deliverable is TWO artifacts, not one
Operator's own derivation, which corrected the question as posed:

> **"3 resonates, but 2 is a one-off and 1 is liable to be rerun periodically"**

**Ruled**: both subjects are in scope, as **two artifacts with different
cadences** —
- **A one-off**: the state of this work — what was built, what it proves, what is blocked, what it costs.
- **A recurring readout**: the business insights themselves, with its own cadence and template.

*(The question offered subject as the only axis. The operator identified
lifecycle as the axis that actually matters. Recorded because the question was
flawed, not the answer.)*

### R-6 · Audience sequencing — EXEC FIRST, TEAM LATER
Same eventual scope; different order. The team-facing surface follows once demand
for it is established — which remains unproven (see UV-P-2 above).

### R-7 · D-4 / gate-(b) scope — SCOPED TO ASANA WRITES
**Ruled**: the mutable-recipient-set modal fires on **Asana writes only**.
`#account-health` is distinguished as an opted-in internal channel. **Slack
delivery stays autonomous.**

This closes the §OPEN question carried by
`RULING-operator-gate-b-modal-2026-08-12.md`, which had recorded it as
**undecided in both directions**. It is now decided in one.

**Named tradeoff, ruled with eyes open**: reading (a)'s failure mode is
**silent** — if the channel is more reachable than assumed, nothing signals it.
That premise is no longer unverified; see R-14.

### R-8 · D-6 — a `k of n` denominator is NOT a third number
**Ruled**: a denominator is a completeness statement, not an age. Readouts may
carry `k of n`. Precedent already ships (`{N} in-scope sections`).

**Fenced by recommendation, accepted as recorded**: this ruling covers
**denominators specifically**. *"It is a different kind of claim"* is exactly the
argument a future seat would reuse for a fourth number — **no further exceptions
without a new ruling.**

### R-9 · D-2 / GATE-FORK — DEFERRED
**Ruled: defer.** The fork governs the **team-facing phase**, which is now second.

**Named revisit trigger: the team phase begins.**

Rationale recorded from the option text the operator selected: ruling A-vs-B on
unproven demand, against a surface PT-02 measured as narrowed **32 Mission-A
lines to 1 Mission-B line**, would be ruling over a named block.

⚠ **Unconfirmed assumption** — see §NOT COVERED item 3 on the 2026-08-18 date.

### R-10 · D-5 — MOOTED BY R-9, not ruled
D-5 (which retrospective route, and on what terms) governs **the Mission-A limb
only**. With GATE-FORK deferred, D-5 is deferred with it. **It is not ruled and
must not be recorded as ruled.** The probe (R-2) will still inform it when it
returns.

### R-11..R-13 · Routings — ALL FOUR ACCEPTED

| routing | disposition |
|---|---|
| **S2S authorization gap → security rite** | **ACCEPTED.** `require_service_claims` authenticates but does not authorize; an Asana board write is gated on **fleet membership, not permission**, while a cache-refresh one file away is permission-gated. **CR-1 is currently the only control.** No incident; nothing exercised. *(Promotes PROPOSED CARD-FU-6.)* |
| **TemporalFilter defect → fix** | **ACCEPTED.** Shipped-code correctness: offers merely **created** over a weekend are reported as having **moved**. Reachable from the CLI today. Active-vs-latent pending R-2. |
| **Log-retention coupling → SRE** | **ACCEPTED.** The ECS log group's 30-day retention is declared in **neither repo** — inherited from a third repo at a pinned `ref=`, mutable by a bump leaving **zero diff anywhere**. |
| **100-campaign cap → card** | **ACCEPTED — CARD-FU-5 is hereby OPENED by operator ruling.** Six operator surfaces, all coincident, no leading indicator. *(A sprint declined to open it on the ground that only the operator may; that restraint is discharged here.)* |

**Recommended sequencing** (recommendation, not ruled): S2S security first — it
is the only one where the current control is a *process* fence rather than a
technical one. TemporalFilter second, once the probe classifies it.

### R-14 · UV-P-S3-1 — CLOSED BY OPERATOR ATTESTATION
> **"I already know it's controlled"**

`#account-health` membership **is internally controlled**. Recorded as
**operator-attested fact**, not as a probe result — the evidence class is
explicitly named so a later seat can weigh it correctly. This discharges the
load-bearing premise under R-7.

### R-15 · The telos gains an EXEC-PHASE RUNG
**Ruled**: keep rung 4 intact (*"a teammate names a figure back to you and makes
a board change they attribute to it"*) and **add a parallel bar for the exec
reader**.

**Fence, recommended and recorded**: the exec rung **does NOT substitute for rung
4**, and **neither may be graded in place of the other**. The named risk of two
ladders is grading against whichever is easier; this fence is what prevents it.

**Recommendation divergence, recorded**: the recommendation was *"leave it honest
as unmet"*, on the ground that editing a measure to fit the work is the move this
crusade normally refuses. **The operator ruled otherwise**, on the ground that a
measure measuring nothing you are doing is inert. That governs.

### R-16 · The exec one-off — ORIENTATION register, drafted AFTER the probe
**Ruled**: it is an **orientation document, not a decision document** —
deliberately, *"to keep 1-3 open"*: whether to keep investing, whether to trust
the numbers, and what is broken and what it costs must all remain **available**
to the reader rather than pre-selected by the author.

**Drafted after the probe returns**, so it need not hedge on whether a filed
defect is active.

**Recommendation divergence, recorded, and the operator's reasoning is the
stronger one**: the recommendation was *"whether to trust the numbers"* (option
2), on the ground that epistemics is what this crusade built. **That would have
pre-selected one decision and framed the other two out — the same
narrowing-by-accumulation failure PT-02 caught in the fork surface.** The
operator's reading preserves optionality. Adopted.

---

## §2 NOT COVERED — recorded so nothing is silently absorbed

Under the standing discipline — *nothing the operator did not explicitly rule on
may be recorded as decided* — the following remain **UNRULED**:

1. **UV-P-2** — *has the offers team asked for anything?* **Still open.** R-1
   redirected the audience; it did not answer this. Demand for the team-facing
   surface remains unproven, and `K-SW-1` still holds that a null answer would be
   mission-reshaping rather than an obstacle.
2. **D-5** — the retrospective route. Deferred with R-9, **not ruled**.
3. **⚠ The 2026-08-18 interaction with R-9.** The record states GATE-FORK is
   *"free until 2026-08-18"*. This ruling **assumes** that means the *deferral* is
   free until then, with the window fence binding **producer deploys** rather than
   the decision. **That assumption is UNVERIFIED.** If something changes on the
   18th for an unruled fork, R-9's trigger may need to fire earlier. **Flagged, not
   resolved.**
4. **Telos ratification (OS-4)** — the telos is still `status: PROPOSED`. R-15
   adds a rung to an unratified document; it does not ratify it.
5. **The exec rung's exact wording** — R-15 rules that one exists and how it
   relates to rung 4. Its text is undrafted.
6. **K-0b** — whether the existing ratification record discharges it. Operator-owned.
7. **CR-2 access** · **OS-6** · **OS-7** — untouched.
8. **G4′** — adopted *inside* the S1 artifact by its author; **not operator-ruled**.
9. **The recurring insights readout's cadence, template and content** — R-5 rules
   that it exists and recurs; nothing about its shape is decided.
10. **Whether the `.sos/wip` corpus more broadly should be promoted.** R-3 rules
    on **the contract**, not on the frames, shapes, W-1 evidence or DETERMINATION
    files that share the same gitignored, non-durable home.

---

## §3 WHAT THIS UNBLOCKS

**Immediately actionable, no further ruling needed:**
- **K-0c** becomes mechanical: promote the contract to `.ledge/decisions/`, apply
  the ratified §3 amendment in place with superseded text struck and standing,
  one PR. **K-0c → K-1 unblocks**, leaving **K-0b** as the sole remaining
  precondition (K-0a passed 2026-08-12).
- **Four routings** dispatch.
- **S1's item 1b and §2.7 row 3** re-derive under R-4.
- **S4's K-lane attestation** narrows under R-4.
- The **telos** gains its exec-phase rung under R-15.

**Sequenced behind the probe (R-2):**
- The **exec one-off**, drafted as an orientation document.
- The **TemporalFilter** fix, prioritised by active-vs-latent.

**Deferred with named triggers:**
- **GATE-FORK** → the team phase begins.
- **D-5** → with the fork.

**Closed today**: D-3, D-4, D-6, D-7, UV-P-S3-1, and the §OPEN scope question
carried since 2026-08-12.

---

## §4 ADDENDUM — four further rulings, same session, arising from executing R-3

R-3 made K-0c executable. Executing it surfaced a governance conflict between two
ratified instruments that **no existing ruling resolved**. The transcription seat
stopped rather than resolving it — correctly; resolving it would have been
authoring a clause. Four rulings followed.

### R-17 · THE FENCE — amend IN-FENCE and re-baseline the receipt
**The conflict**: the ratified §1.2 amendment targets text sitting **39 lines
inside a 498-line `verbatim_core` byte-identity fence**. The fence carries a live
mechanical receipt (a recorded `diff` asserting zero byte-deltas, 497 lines) which
was **re-verified intact** at ruling time — exit 0, empty diff. ADR-007 is
**silent**: zero hits for `verbatim_core` / `extraction-fence` / `byte-for-byte`
across all 1,375 lines, despite its §3 citing "fence line 150".

**Ruled: amend in place, re-baseline §B's receipt, record why.**

**Consequence, ruled with eyes open**: the fence's guarantee changes permanently
from *"byte-identical to source"* to *"byte-identical as of the [A-2026-08-12]
amendment."*

⚠ **DISCLOSED LIMITATION, ruled to be carried and NOT fixed**: the fence's source
(`.sos/wip/DESIGN-s1-arch-watermark-contract-2026-08-11.md`) is **still
gitignored**, so the re-baselined receipt is **not reproducible from a fresh
clone**. R-3 promoted the contract only; **§NOT COVERED item 10 explicitly leaves
the wider `.sos/wip` corpus unruled** and that stands. The seat is instructed to
state this gap in the §B record and **not** to promote the source.

**Recommendation divergence, recorded**: the recommendation was *"seal the fence,
supersede by reference"* — preserving an intact receipt and matching the model
the `non_amendable` charter uses in its own §7. **The operator ruled otherwise;
that governs.**

### R-18 · AMB-2 — transcribe `(binding)` VERBATIM
The draft text reads `**VERIFICATION GRAIN (binding).**`; R-i softened the clause
binding→advisory; the overlay says *"preserved verbatim"*.

**Ruled: verbatim.** **Required mitigation**: the R-i softening sits **adjacent**
in the amendment block, stating that P-5 **remains operative** and that the
advisory character **spares contract-fence ceremony only and does not open the
denominator** (R-alt: escalate only at the wall, receipts required). Rationale for
the mitigation: four build legs sign this contract, and no leg may reach
`(binding)` without reaching the ruling that qualifies it.

### R-19 · AMB-3 — STRIKE the FORK-B paragraph
`CONTRACT…:179-182` asserts the content-only law being superseded. ADR-007 never
mentions it (**zero** hits for `FORK-B`).

**Ruled: strike it with the law it restates.** **Required mitigation**: the
supersession note **preserves its code citations** (`substrate/freshness.py:10-11`,
`:13-14`). The strike removes a superseded **assertion**; it must not discard
**evidence** that may still be true of the substrate on its own terms.

**Recommendation divergence, recorded**: the recommendation was *"amend it to
point forward"*, on the ground that striking loses live provenance. **Operator
ruled otherwise; the citation-preservation mitigation is the accommodation.**

### R-20 · AMB-4 — PIN `verification_backfill_used` now
**Ruled: pin it.** Transcribe the name as the ratified amendment writes it.

⚠ **FLAGGED, EXPLICITLY UNRULED**: pinning this into the frozen naming fence
creates tension with **R-O3**, which **DELEGATED** the spelling to the architect
at the producer-leg PR, and with `ADR-007:695`'s own `[spelling pending — §8 O-3]`
marker. Under the pin, R-O3's PR would be re-amending a **frozen** contract to
change it — which converts a delegation into a confirmation in practice.

**The operator ruled the pin. The operator did NOT rule on R-O3's status.**
**R-O3 is NOT recorded as discharged.** Any later seat reading the pin as having
settled R-O3 is reading something the operator did not say.

**Recommendation divergence, recorded**: the recommendation was *"land it marked
pending"*, matching what ADR-007 itself already does.

### §4a — a premise error in the main thread's charge, corrected by the seat
The dispatch named `CHARTER-decision-space-of-record-2026-07-30.md` as the
[A-2026-08-03] amendment precedent. **It is not.** That file is
`non_amendable: true` and its §7 forbids edits — *"amendments… are new operator
rulings on a separate channel, never edits to this file."* The precedent actually
landed on **`CHARTER-substrate-v2-epoch-2026-07-27.md`** (PR #298, merge
`9797579c`): frontmatter `amended:` line, `> **[A-2026-08-03]**` blockquotes
inserted after the amended text, `status` untouched, **zero deletions**.

Recorded because the precedent was load-bearing on *how* to strike, and because
the correction came from the seat rather than from the charging thread —
consistent with the method finding that **a second reader going one hop further
is what catches this class**.

### §4b — a degradation in K-0c's own exit criterion, disclosed not fixed
The canonical contract is **still untracked** (`git status` → `??`). It is
un-ignored by `.gitignore:129` but was never committed. **So the K-0c PR ADDS the
file**: the struck-and-standing text will be visible in the body but **will not
render as a diff**. If the purpose of *"one PR, superseded text struck and
standing"* is a reviewable diff, that purpose is degraded here. **Disclosed in
the PR description rather than worked around.**

### §4c — Limb B, found by checking rather than assuming
The §3 amendment has a **second limb** the charge did not anticipate: **§E.2's
roster goes twelve → fifteen names** (`verified_at`,
`verification_age_seconds`, `verification_backfill_used`), at `CONTRACT…:892-911`
— **outside** the fence and fence-safe. It **cannot precede Limb A**: §E's own
precedence rule (`CONTRACT…:863-865`) makes any §E.2 name the fence does not carry
"the error". **Both limbs ride one PR**, satisfying K-0c's own requirement rather
than violating it.
