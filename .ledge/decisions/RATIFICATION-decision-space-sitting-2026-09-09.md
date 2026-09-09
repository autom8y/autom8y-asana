# RATIFICATION — decision-space sitting, 2026-09-09

**Convened:** operator, at close of the overnight seam, to unblock the next 8 hours.
**Form:** `/interview`, three adaptive rounds, ten questions, neutral framing with assumptions
declared before each set and a reject-the-premise option in every set.
**Status:** RATIFIED. Rulings **R-73 … R-82** extend the decision-space of record by reference.
**Never-grantable floor UNTOUCHED:** rotation-execution · customer-visible outbound acts ·
business-of-record identity mints. Nothing below reaches these.

---

## §1 WHAT WAS DECIDED

### R-73 — R-35 CONVERTS to gate-conditional · BINDING
The EBI freeze is no longer a wait-on-a-human. It becomes a wait-on-a-mechanism.
**It is NOT discharged and NOT lifted.** Applies remain forbidden until §R-74 is satisfied.

### R-74 — The release condition is CONJUNCTIVE · BINDING
Applies resume only when **BOTH**:
1. a **fail-closed required check** blocks `services/email-booking-intake/**` merges, **AND**
2. the **salkin diff is receipted** (R-76/R-77).
*Neither alone releases.* This resolves a gap the first round created and did not expose: two
release conditions were chosen in separate questions with no stated relation.

### R-75 — The gate carries NO FLAG · BINDING
The gate blocks `services/email-booking-intake/**` **unconditionally**. There is no freeze flag, no
default state, and no owner to name — **because a control with no configurable state cannot be
misconfigured.** Unblocking is an explicit, reviewable, attributable edit to the gate itself.
> **Rationale of record:** R-35's own defect was an unnamed instant and default disposition. A
> flag-driven gate would have reproduced that defect *inside its own cure.* Removing the state
> removes the defect class.
**Accepted cost:** coarse. Every EBI merge needs a deliberate gate change, including ones the
operator would have waved through.

### R-76 — The salkin read goes to a RITE-DISJOINT seat, method MANDATED · BINDING
**Method, binding and non-negotiable:** materialize **both complete filesystems** and diff the
**trees**. **NEVER per-layer.**
> **Basis:** A17 diffed layers 12/13 in isolation, concluded "the image changed nothing in the
> application source," and **a freeze was lifted on that false premise.** A20 retracted it in full.
> Two further layers (11,861 B and 3,182 B) overlay `rules.py` and `intake_classify.py` — precisely
> two of the three source files #2087 modified. **Critic-never-author, applied to a measurement.**
**Declared cost:** the disjoint seat lacks the context that makes the result meaningful.

### R-77 — The read is defined so it CANNOT be inconclusive · BINDING
Output is a **list of changed paths**. **An EMPTY list is a valid, conclusive answer — not a
failure.** Therefore "inconclusive" can only mean **the measurement itself failed**, which
**fails closed and escalates.**
> **Residual, recorded and NOT resolved:** *what changed* is not *whether it mattered.* A path list
> may still leave a judgement for the operator. **This is a known gap, not an oversight.**

### R-78 — Clause (c) SPLITS · BINDING
- **(c1) ANTI-ANECDOTE** — closable now, needs no denominator.
- **(c2) COVERAGE** over a ruled population — **BOOKED OPEN.**
Follows the **O-8 precedent**: compose, do not collapse.
> **Provenance, stated plainly:** the operator's words at framing were *"3 sounds good, but for all
> active clients—not just one."* The telos rendered that as a universal quantifier over an
> unenumerable set, which two lanes independently proved unfalsifiable. **The split adopts the
> instruction and retires the rendering.**

### R-79 — (c1) closes at TWO DISTINCT OFFICES, TWO-SIDED · BINDING
(c1) closes when **≥ 2 distinct offices** each carry **BOTH** a live attributed booking **AND** a
failure naming that office **with its kind**.
**Declared weakness, on the record:** *two is arbitrary.* It is the smallest number that is not one,
and is defensible only as the literal encoding of *"not just one."*

### R-80 — Production STAYS on `4e0b41f` pending the read · BINDING
**DO NOT RESTORE.** R-35 forbids applies **either way**; a restorative apply is a second
unauthorized apply. Compounding hazard, measured tonight: **applies roll FORWARD to a fresh build,
not back to the tfvars pin**, so a "restorative" apply would silently erase the out-of-band image
**with no receipt emitted anywhere.**
**Containment, measured:** image intact in ECR · **no lifecycle policy ⇒ no reaping clock** ·
0 of 62 open PRs auto-merge armed · production healthy (48 invocations / 0 errors).

### R-81 — Overnight order: GATE → CLAUSE (b) → S-06 · BINDING
Only the gate is on R-35's critical path (R-74).
**Counter-argument recorded rather than suppressed:** the gate is *governance, not product*, and
clause (b) is the only clause whose remaining distance is **time rather than unknown** — the first
such moment in 47 addenda. **The operator chose process-first on the night after an incident, with
that trade stated.**

### R-82 — The clause-(b) cure is AUTHORED AND PARKED, NOT MERGED · BINDING
Per **S2-7**, which the operator himself ratified after a seat corrected him: *"AUTHOR the deletion,
PARK it unmerged. Realization waits on the freeze."*

---

## §2 WHAT WAS EXPLICITLY DEFERRED

| deferred | why | unblocked by |
|---|---|---|
| **(c2) coverage** | population is un-ruled | WS-JOIN + an identity ruling |
| **O-2 §A · O-4(a)(b)(c) · O-7** | not raised at this sitting | the fork sheet |
| **F-1…F-7** | **one identity ruling with seven faces**, not seven rulings | a single architectural sitting |
| **O-4(b) — the 5 unredacted `office_phone` emissions** | live PII, operator-owned, and it sits ~20 lines from the clause-(b) edit | its own adjudication; **NOT a rider** |
| **The `phone_hash` defect, SECOND instance** | `book_appointment.py:45-54`, pre-existing on main; anonymity set of 1 | operator; **not cured tonight** |
| **Whether the Damian brief was ever SENT** | unanswered across all records | operator |
| **What the salkin change MEANT** | R-77 yields *what* changed, not *whether it mattered* | operator, after the read |

---

## §3 ★ ASSUMPTIONS THAT REMAIN UNCONFIRMED

1. **★ THE OPERATOR SELECTED MY RECOMMENDATION TEN TIMES OUT OF TEN.** That is equally consistent
   with the recommendations being sound **and with my framing having led the witness.** I cannot
   distinguish these from inside, and I am recording it as a defect risk in the sitting itself
   rather than as validation. **Any of R-73…R-82 should be re-openable on that ground alone.**
2. **R-35's purpose** was to prevent an un-analyzed change from being silently erased. If it was
   broader, R-73's conversion is under-inclusive.
3. **The gate is C-INERT in `autom8y`.** Verified for the `service-deploy-dispatch` route by two
   seats — and **explicitly bounded by the substrate lane: 91 workflow files, one route cleared, NOT
   the repo.** That lane refused to launder an uncontrolled empty search into a safety claim.
   **Must be re-cleared against the full required-context set at the head before pushing.**
4. **"Active clients" has no enumerable definition.** Two lanes, disjoint corpora, both declined to
   invent one — this lane because the predicate is **unfalsifiable**, the substrate lane because a
   wrong answer is **irreversible**. Two observations, not one echoed twice.
5. **#2089's seat is not established.** Both merges carry the shared operator credential. **This
   seat merged #2087.** Nothing here claims or disclaims #2089.

---

## §4 WHAT THIS SITTING DOES NOT DO
It does not lift R-35. It does not restore production. It does not discharge any clause of the
realization predicate — **all four remain WAITING.** It does not cure the PII. It does not answer
what `salkin-safe-routing` changed.

> **`Verified-realized` = a LIVE attributed booking naming that office, TWO-SIDED — a failure for
> the SAME office also names it, WITH ITS KIND, never blank — held across ALL active clients, not
> one. NOT "PRs merged". DONE IS A BAR, NOT A DATE.**
